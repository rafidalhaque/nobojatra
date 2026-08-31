"""S3-compatible object storage. SSE enforced on every put (spec 5, 11.1).

No filetype / size / count validation anywhere by design (spec 5)."""

import uuid
from typing import BinaryIO

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()

_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    region_name=settings.s3_region,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    config=Config(signature_version="s3v4"),
)


def ensure_bucket() -> None:
    existing = {b["Name"] for b in _client.list_buckets().get("Buckets", [])}
    if settings.s3_bucket not in existing:
        _client.create_bucket(Bucket=settings.s3_bucket)


def put(fileobj: BinaryIO, content_type: str | None) -> str:
    key = f"posts/{uuid.uuid4().hex}"
    extra = {"ServerSideEncryption": settings.s3_sse}
    if content_type:
        extra["ContentType"] = content_type
    _client.upload_fileobj(fileobj, settings.s3_bucket, key, ExtraArgs=extra)
    return key


def open_stream(key: str):
    """Returns (iterator, content_type, content_length)."""
    obj = _client.get_object(Bucket=settings.s3_bucket, Key=key)
    return obj["Body"].iter_chunks(64 * 1024), obj.get("ContentType"), obj.get("ContentLength")


def delete(key: str) -> None:
    _client.delete_object(Bucket=settings.s3_bucket, Key=key)
