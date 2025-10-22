import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Qwen API Configuration
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_api_url: str = os.getenv(
        "QWEN_API_URL",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )

    # Spring Boot gRPC Configuration
    spring_boot_grpc_host: str = os.getenv("SPRING_BOOT_GRPC_HOST", "localhost")
    spring_boot_grpc_port: int = int(os.getenv("SPRING_BOOT_GRPC_PORT", "9090"))

    # Service Configuration
    service_port: int = int(os.getenv("PYTHON_SERVICE_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # AI Model Configuration
    model_name: str = "qwen-vl-max"
    max_retries: int = 3
    timeout_seconds: int = 120

    class Config:
        env_file = "..env"

settings = Settings()
