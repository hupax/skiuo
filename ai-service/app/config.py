import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Qwen API Configuration
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "sk-ca9c7b9a2f33471d8d092851ccc74b68")
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
    ai_model_name: str = "qwen-vl-max"  # 重命名避免与 pydantic 的 model_ 命名空间冲突
    max_retries: int = 3
    timeout_seconds: int = 120

    # Minio Configuration (S3 Compatible)
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "https://minio-api.supanx.net")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "test")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_public_url: str = os.getenv("MINIO_PUBLIC_URL", "https://minio-api.supanx.net/test/")

    class Config:
        env_file = "..env"
        protected_namespaces = ('settings_',)  # 修改保护的命名空间

settings = Settings()
