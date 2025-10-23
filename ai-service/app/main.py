from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
import logging
import asyncio
import base64
from pathlib import Path
from typing import Optional

from app.config import settings
from app.qwen_client import QwenVisionClient
from app.grpc_client import SpringBootGrpcClient
from app.context_manager import ContextManager
from app.video_processor import VideoProcessor

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
    3. 逐个窗口进行 AI 分析
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
        # 1. 使用滑动窗口切片视频
        logger.info(f"Slicing video with sliding window...")
        windows = video_processor.slice_video_with_sliding_window(video_path, session_id)
        logger.info(f"Created {len(windows)} windows for analysis")

        if not windows:
            logger.warning(f"No windows created for video {video_path}")
            return VideoAnalysisResponse(
                session_id=session_id,
                total_windows=0,
                status="completed",
                message="Video too short, no windows created"
            )

        # 2. 逐个窗口分析
        token_index = 0

        for window in windows:
            logger.info(
                f"Analyzing window {window.window_index}/{len(windows)}: "
                f"{window.start_time:.1f}s - {window.end_time:.1f}s"
            )

            # 获取前一个窗口的摘要（保持连贯性）
            previous_summary = context_manager.get_previous_window_summary(session_id)

            # 发送窗口标记到前端
            window_marker = f"\n\n📹 [分析窗口 {window.window_index + 1}/{len(windows)}] ({window.start_time:.1f}s - {window.end_time:.1f}s) "
            timestamp = int(asyncio.get_event_loop().time() * 1000)
            await grpc_client.save_analysis(
                session_id=session_id,
                content=window_marker,
                token_index=token_index,
                timestamp=timestamp
            )
            token_index += 1

            # 3. AI 分析窗口视频
            accumulated_response = ""
            try:
                async for token in qwen_client.analyze_video_streaming(
                    video_path=window.file_path,
                    start_time=window.start_time,
                    end_time=window.end_time,
                    previous_summary=previous_summary
                ):
                    accumulated_response += token

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
                        logger.error(f"Failed to save token {token_index} for session {session_id}")

                # 4. 保存窗口摘要（用于下一个窗口的上下文）
                if accumulated_response:
                    # 截取前 300 字符作为摘要
                    summary = accumulated_response[:300]
                    context_manager.add_window_summary(session_id, window.window_index, summary)
                    logger.info(
                        f"Window {window.window_index} analysis completed: "
                        f"{len(accumulated_response)} chars"
                    )

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

        # 5. 清理窗口文件
        try:
            video_processor.cleanup_windows(session_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup windows: {e}")

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
