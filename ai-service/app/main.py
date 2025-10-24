from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
import logging
import asyncio
import base64
from pathlib import Path
from typing import Optional
import os

# Load .env file explicitly (before importing settings)
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
logger_init = logging.getLogger(__name__)
logger_init.info(f"Loading environment from: {env_path}")

from app.config import settings
from app.qwen_client import QwenVisionClient
from app.grpc_client import SpringBootGrpcClient
from app.context_manager import ContextManager
from app.video_processor import VideoProcessor
from app.minio_client import MinioClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
qwen_client = QwenVisionClient()
grpc_client = SpringBootGrpcClient()
context_manager = ContextManager()
video_processor = VideoProcessor(
    window_size=15.0,  # 15 seconds
    step_size=10.0,    # 10 seconds (5s overlap)
    output_dir="./temp_windows"
)
minio_client = MinioClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("StreamMind AI Service starting up...")
    logger.info(f"Qwen API configured: {bool(settings.qwen_api_key)}")
    logger.info(f"Spring Boot gRPC: {settings.spring_boot_grpc_host}:{settings.spring_boot_grpc_port}")
    yield
    # Shutdown
    logger.info("StreamMind AI Service shutting down...")
    await grpc_client.close()

app = FastAPI(title="StreamMind AI Service", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "StreamMind AI Service",
        "status": "running",
        "model": settings.ai_model_name
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws/analyze/{session_id}")
async def websocket_analyze(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint to receive frames from Node.js signaling service
    and stream analysis results back
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session: {session_id}")

    token_index = 0
    frame_count = 0

    try:
        # Create debug directory for this session
        debug_dir = Path(f"./debug_frames/{session_id}")
        debug_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving debug frames to: {debug_dir}")

        while True:
            # Receive frame data (base64 JPEG) from Node.js
            data = await websocket.receive_text()

            frame_count += 1
            logger.info(f"Received frame {frame_count} for session {session_id}, size: {len(data)} bytes")

            # Save frame to debug directory
            try:
                import time
                timestamp = int(time.time())
                frame_path = debug_dir / f"frame_{frame_count:04d}_{timestamp}.jpg"
                # Decode base64 and save
                if data.startswith("data:image"):
                    # Remove data URI prefix if present
                    image_data = data.split(',')[1]
                else:
                    image_data = data

                with open(frame_path, 'wb') as f:
                    f.write(base64.b64decode(image_data))
                logger.info(f"[帧{frame_count}] Saved to: {frame_path.name}")
            except Exception as e:
                logger.error(f"Failed to save debug frame {frame_count}: {e}")

            # Get conversation context
            context = context_manager.get_context(session_id)

            # Analyze frame with Qwen
            try:
                logger.info(f"[帧{frame_count}] Starting AI analysis...")
                accumulated_response = ""

                # 先发送帧号标记到前端
                frame_marker = f"\n\n📸 [分析帧 {frame_count}] "
                await websocket.send_text(frame_marker)

                async for token in qwen_client.analyze_frame_streaming(data, context):
                    # Accumulate the complete response
                    accumulated_response += token

                    # Send token back to Node.js (optional)
                    await websocket.send_text(token)

                    # Send token to Spring Boot via gRPC
                    timestamp = int(asyncio.get_event_loop().time() * 1000)
                    success = await grpc_client.save_analysis(
                        session_id=session_id,
                        content=token,
                        token_index=token_index,
                        timestamp=timestamp
                    )

                    if success:
                        token_index += 1
                    else:
                        logger.error(f"Failed to save token {token_index} for session {session_id}")

                # Update context with the complete analysis for continuity
                # Add as assistant's response
                if accumulated_response:
                    summary = f"[帧{frame_count}分析] {accumulated_response[:200]}..."  # 保存摘要避免上下文过长
                    context_manager.add_to_context(session_id, summary, role="assistant")
                    logger.info(f"[帧{frame_count}] Analysis completed: {len(accumulated_response)} chars")

            except Exception as e:
                logger.error(f"Error analyzing frame: {e}", exc_info=True)
                await websocket.send_text(f"ERROR: {str(e)}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
    finally:
        # Clean up context
        context_manager.clear_context(session_id)
        logger.info(f"Cleaned up context for session: {session_id}")


# ========== 视频分析端点（新方案）==========

class VideoAnalysisRequest(BaseModel):
    """视频分析请求"""
    session_id: str
    video_path: str


class VideoAnalysisResponse(BaseModel):
    """视频分析响应"""
    session_id: str
    total_windows: int
    status: str
    message: str


@app.post("/analyze-video", response_model=VideoAnalysisResponse)
async def analyze_video(request: VideoAnalysisRequest):
    """
    分析上传的视频文件

    流程：
    1. 接收视频文件路径
    2. 使用滑动窗口切片视频
    3. 逐个窗口进行 AI 分析（直接分析视频）
    4. 流式发送结果到 Spring Boot（gRPC）
    5. 管理上下文连贯性
    """
    session_id = request.session_id
    video_path = request.video_path

    logger.info(f"Received video analysis request for session {session_id}: {video_path}")

    # 验证视频文件存在
    if not Path(video_path).exists():
        logger.error(f"Video file not found: {video_path}")
        raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")

    try:
        # 1. 切片视频为滑动窗口
        logger.info(f"Slicing video into windows...")
        windows = video_processor.slice_video_with_sliding_window(video_path, session_id)

        if not windows:
            logger.warning(f"No windows created for video {video_path}")
            return VideoAnalysisResponse(
                session_id=session_id,
                total_windows=0,
                status="completed",
                message="Video too short, no windows created"
            )

        logger.info(f"Created {len(windows)} windows for analysis")

        # 2. 逐个窗口上传到Minio并进行 AI 分析
        token_index = 0
        previous_summary = None
        uploaded_urls = []  # 记录所有上传的Minio URL，用于最后清理

        for window in windows:
            logger.info(
                f"Analyzing window {window.window_index + 1}/{len(windows)}: "
                f"{window.start_time:.1f}s - {window.end_time:.1f}s"
            )

            # 发送窗口标记到前端
            window_marker = f"\n\n📹 [分析窗口 {window.window_index + 1}/{len(windows)}] ({window.start_time:.1f}s - {window.end_time:.1f}s)\n"
            timestamp = int(asyncio.get_event_loop().time() * 1000)
            await grpc_client.save_analysis(
                session_id=session_id,
                content=window_marker,
                token_index=token_index,
                timestamp=timestamp
            )
            token_index += 1
            logger.info(f"Sent window marker for window {window.window_index + 1}")

            # 上传窗口视频到Minio
            video_url = None
            try:
                logger.info(f"Uploading window {window.window_index} to Minio...")
                video_url = minio_client.upload_video(window.file_path)
                uploaded_urls.append(video_url)
                logger.info(f"Window uploaded: {video_url}")
            except Exception as e:
                logger.error(f"Failed to upload window {window.window_index} to Minio: {e}")
                error_msg = f"\n[ERROR] 上传窗口 {window.window_index} 到Minio失败: {str(e)}\n"
                timestamp = int(asyncio.get_event_loop().time() * 1000)
                await grpc_client.save_analysis(
                    session_id=session_id,
                    content=error_msg,
                    token_index=token_index,
                    timestamp=timestamp
                )
                token_index += 1
                continue  # 跳过这个窗口的分析

            # 获取上下文
            context = context_manager.get_context(session_id)

            # AI 分析窗口视频（使用Minio公网URL）
            accumulated_response = ""
            token_count = 0
            try:
                async for token in qwen_client.analyze_video_streaming(
                    video_path=video_url,
                    start_time=window.start_time,
                    end_time=window.end_time,
                    context=context,
                    previous_summary=previous_summary
                ):
                    accumulated_response += token
                    token_count += 1

                    # 发送 token 到 Spring Boot
                    timestamp = int(asyncio.get_event_loop().time() * 1000)
                    success = await grpc_client.save_analysis(
                        session_id=session_id,
                        content=token,
                        token_index=token_index,
                        timestamp=timestamp
                    )

                    if success:
                        token_index += 1
                    else:
                        logger.error(f"Failed to save token {token_index}")

                # 检查是否有分析结果
                if accumulated_response.strip():
                    # 保存完整的分析结果作为上下文
                    context_manager.add_to_context(session_id, accumulated_response[:500], role="assistant")
                    previous_summary = accumulated_response[:200]  # 保留前200字符作为摘要
                    logger.info(f"Window {window.window_index + 1} analyzed: {len(accumulated_response)} chars, {token_count} tokens")
                else:
                    # 如果没有返回内容，记录警告并发送提示
                    logger.warning(f"Window {window.window_index + 1} returned empty response")
                    empty_msg = f"[警告] 此窗口分析未返回内容\n"
                    timestamp = int(asyncio.get_event_loop().time() * 1000)
                    await grpc_client.save_analysis(
                        session_id=session_id,
                        content=empty_msg,
                        token_index=token_index,
                        timestamp=timestamp
                    )
                    token_index += 1

            except Exception as e:
                logger.error(f"Error analyzing window {window.window_index}: {e}", exc_info=True)
                error_msg = f"\n[ERROR] 分析窗口 {window.window_index} 时出错: {str(e)}\n"
                timestamp = int(asyncio.get_event_loop().time() * 1000)
                await grpc_client.save_analysis(
                    session_id=session_id,
                    content=error_msg,
                    token_index=token_index,
                    timestamp=timestamp
                )
                token_index += 1

        logger.info(f"Video analysis completed for session {session_id}, total tokens: {token_index}")

        # 3. 清理Minio上传的文件
        logger.info(f"Cleaning up {len(uploaded_urls)} uploaded files from Minio...")
        for url in uploaded_urls:
            try:
                minio_client.delete_video(url)
            except Exception as e:
                logger.warning(f"Failed to delete Minio file {url}: {e}")

        # 4. 清理本地窗口文件
        try:
            video_processor.cleanup_windows(session_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup local windows: {e}")

        return VideoAnalysisResponse(
            session_id=session_id,
            total_windows=len(windows),
            status="completed",
            message=f"Successfully analyzed {len(windows)} windows"
        )

    except Exception as e:
        logger.error(f"Video analysis failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
