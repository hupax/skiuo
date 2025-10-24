"""
Minio Client - Upload video files and return public URLs
Compatible with S3 API
"""
import logging
from pathlib import Path
from typing import Optional
import uuid
from urllib.parse import urljoin

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

from app.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    """Minio客户端（S3兼容）"""

    def __init__(self):
        """初始化Minio客户端"""
        self.endpoint_url = settings.minio_endpoint
        self.bucket_name = settings.minio_bucket
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key
        self.public_url = settings.minio_public_url

        if not all([self.endpoint_url, self.bucket_name]):
            logger.warning("Minio configuration not complete, upload will not work")
            self.s3_client = None
        else:
            try:
                # 创建S3客户端（Minio兼容S3 API）
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1'  # Minio doesn't require specific region
                )
                logger.info(f"Minio client initialized: bucket={self.bucket_name}, endpoint={self.endpoint_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Minio client: {e}")
                self.s3_client = None

    def upload_video(self, local_path: str, object_name: Optional[str] = None) -> str:
        """
        上传视频文件到Minio并返回公网URL

        Args:
            local_path: 本地文件路径
            object_name: 对象名称，如果不提供则自动生成（格式：videos/{uuid}_{filename}）

        Returns:
            str: 公网访问URL

        Raises:
            Exception: 上传失败时抛出异常
        """
        if not self.s3_client:
            raise RuntimeError("Minio client not initialized, check your configuration")

        # 验证文件存在
        if not Path(local_path).exists():
            raise FileNotFoundError(f"Video file not found: {local_path}")

        # 生成对象名称
        if not object_name:
            filename = Path(local_path).name
            unique_id = str(uuid.uuid4())[:8]
            object_name = f"videos/{unique_id}_{filename}"

        try:
            # 上传文件
            logger.info(f"Uploading {local_path} to Minio as {object_name}...")

            with open(local_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    object_name,
                    ExtraArgs={'ContentType': 'video/webm'}
                )

            # 生成公网URL
            # 如果用户配置了公网URL，使用它；否则使用endpoint
            if self.public_url:
                public_url = urljoin(self.public_url, object_name)
            else:
                # 从endpoint构造URL
                public_url = f"{self.endpoint_url}/{self.bucket_name}/{object_name}"

            logger.info(f"Video uploaded successfully: {public_url}")
            return public_url

        except ClientError as e:
            logger.error(f"Minio error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to upload video to Minio: {e}")
            raise

    def delete_video(self, object_name: str) -> bool:
        """
        删除Minio上的视频文件

        Args:
            object_name: 对象名称（可以从URL解析得到）

        Returns:
            bool: 删除成功返回True
        """
        if not self.s3_client:
            logger.warning("Minio client not initialized, cannot delete")
            return False

        try:
            # 如果传入的是完整URL，解析出object_name
            if object_name.startswith("http"):
                # 从URL提取object_name
                # 例如: https://minio-api.supanx.net/test/videos/xxx.webm -> videos/xxx.webm
                parts = object_name.split(f"{self.bucket_name}/")
                if len(parts) > 1:
                    object_name = parts[-1]
                else:
                    # 尝试从路径中提取
                    from urllib.parse import urlparse
                    parsed = urlparse(object_name)
                    object_name = parsed.path.lstrip('/')
                    # 移除bucket名称前缀（如果存在）
                    if object_name.startswith(f"{self.bucket_name}/"):
                        object_name = object_name[len(self.bucket_name)+1:]

            logger.info(f"Deleting Minio object: {object_name}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Successfully deleted: {object_name}")
            return True

        except ClientError as e:
            logger.error(f"Minio error when deleting {object_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete Minio object {object_name}: {e}")
            return False

    def get_signed_url(self, object_name: str, expires: int = 3600) -> str:
        """
        生成签名URL（用于私有Bucket）

        Args:
            object_name: 对象名称
            expires: URL有效期（秒），默认1小时

        Returns:
            str: 签名URL
        """
        if not self.s3_client:
            raise RuntimeError("Minio client not initialized")

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expires
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise
