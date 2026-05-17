"""MinIO client abstraction."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from common.exceptions import StorageError
from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


def _parse_endpoint(endpoint: str, secure: bool) -> tuple[str, int, bool]:
    """Parse MINIO_ENDPOINT into host, port, and secure flag."""
    if "://" in endpoint:
        parsed = urlparse(endpoint)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        use_ssl = parsed.scheme == "https"
    else:
        host = endpoint.split(":")[0]
        port = int(endpoint.split(":")[1]) if ":" in endpoint else (443 if secure else 80)
        use_ssl = secure
    if not host:
        raise StorageError(f"Invalid MinIO endpoint: {endpoint}")
    return host, port, use_ssl


class MinioStorageClient:
    """MinIO connectivity wrapper driven by configuration."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        host, port, secure = _parse_endpoint(
            self._settings.minio_endpoint, self._settings.minio_secure
        )
        self._client = Minio(
            f"{host}:{port}",
            access_key=self._settings.minio_access_key,
            secret_key=self._settings.minio_secret_key,
            secure=secure,
        )
        self._bucket = self._settings.minio_bucket

    @property
    def bucket(self) -> str:
        return self._bucket

    def validate_connectivity(self) -> bool:
        """Verify bucket is reachable."""
        try:
            return self._client.bucket_exists(self._bucket)
        except S3Error as exc:
            logger.error("MinIO connectivity check failed: %s", exc)
            raise StorageError("MinIO connectivity validation failed") from exc

    def ensure_bucket(self) -> None:
        """Create configured bucket if it does not exist."""
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
                logger.info("Created MinIO bucket=%s", self._bucket)
        except S3Error as exc:
            raise StorageError(f"Failed to ensure bucket {self._bucket}") from exc

    def put_bytes(self, object_key: str, data: bytes, content_type: str = "application/json") -> None:
        """Upload bytes to object storage."""
        from io import BytesIO

        try:
            self._client.put_object(
                self._bucket,
                object_key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            logger.info("Uploaded object bucket=%s key=%s", self._bucket, object_key)
        except S3Error as exc:
            raise StorageError(f"Upload failed for {object_key}") from exc
