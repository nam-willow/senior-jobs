import hashlib
import io
from datetime import timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinIOStorage:
    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        except S3Error:
            pass

    def upload(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """MinIO에 파일 업로드. 업로드된 경로(path) 반환."""
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=path,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return path

    def download(self, path: str) -> bytes:
        """MinIO에서 파일 다운로드."""
        response = self._client.get_object(self._bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_presigned_url(self, path: str, expires: int = 3600) -> str:
        """presigned GET URL 반환 (기본 1시간)."""
        url = self._client.presigned_get_object(
            bucket_name=self._bucket,
            object_name=path,
            expires=timedelta(seconds=expires),
        )
        return url

    def delete(self, path: str) -> None:
        self._client.remove_object(self._bucket, path)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_path(tenant_id: str, file_type: str, filename: str) -> str:
    """MinIO 경로: /{tenant_id}/{pdf|excel}/{filename}"""
    return f"{tenant_id}/{file_type}/{filename}"


_storage: Optional[MinIOStorage] = None


def get_storage() -> MinIOStorage:
    global _storage
    if _storage is None:
        _storage = MinIOStorage()
    return _storage
