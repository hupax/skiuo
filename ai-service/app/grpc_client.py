import grpc
import logging
from typing import Optional

from .config import settings

# Import generated protobuf code
# Note: This will be generated after running protoc
try:
    from app.generated.proto import analysis_pb2, analysis_pb2_grpc
except ImportError:
    try:
        from generated.proto import analysis_pb2, analysis_pb2_grpc
    except ImportError:
        try:
            from app.generated import analysis_pb2, analysis_pb2_grpc
        except ImportError:
            logger = logging.getLogger(__name__)
            logger.warning("Protobuf files not generated yet. Run: python -m grpc_tools.protoc ...")
            analysis_pb2 = None
            analysis_pb2_grpc = None

logger = logging.getLogger(__name__)

class SpringBootGrpcClient:
    def __init__(self):
        self.host = settings.spring_boot_grpc_host
        self.port = settings.spring_boot_grpc_port
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None

        if analysis_pb2_grpc:
            self._connect()

    def _connect(self):
        """Establish gRPC connection"""
        address = f"{self.host}:{self.port}"
        self.channel = grpc.aio.insecure_channel(address)
        self.stub = analysis_pb2_grpc.AnalysisServiceStub(self.channel)
        logger.info(f"gRPC client connected to {address}")

    async def save_analysis(
        self,
        session_id: str,
        content: str,
        token_index: int,
        timestamp: int
    ) -> bool:
        """
        Send analysis token to Spring Boot via gRPC

        Returns:
            bool: True if saved successfully
        """
        if not self.stub:
            logger.error("gRPC stub not initialized (protobuf files missing?)")
            return False

        try:
            request = analysis_pb2.AnalysisRequest(
                session_id=session_id,
                content=content,
                token_index=token_index,
                timestamp=timestamp
            )

            response = await self.stub.SaveAnalysis(request)

            if response.success:
                logger.debug(f"Saved token {token_index} for session {session_id}, ID: {response.saved_id}")
                return True
            else:
                logger.error(f"Failed to save token: {response.message}")
                return False

        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in save_analysis: {e}", exc_info=True)
            return False

    async def close(self):
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
            logger.info("gRPC channel closed")
