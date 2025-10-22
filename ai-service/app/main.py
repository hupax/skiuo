from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.config import settings
from app.qwen_client import QwenVisionClient
from app.grpc_client import SpringBootGrpcClient
from app.context_manager import ContextManager

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

    try:
        while True:
            # Receive frame data (base64 JPEG) from Node.js
            data = await websocket.receive_text()

            logger.debug(f"Received frame for session {session_id}, size: {len(data)} bytes")

            # Get conversation context
            context = context_manager.get_context(session_id)

            # Analyze frame with Qwen
            try:
                async for token in qwen_client.analyze_frame_streaming(data, context):
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

                # Update context with the complete analysis
                # (In a real implementation, accumulate the tokens)
                context_manager.add_to_context(session_id, "Analysis completed for frame")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
