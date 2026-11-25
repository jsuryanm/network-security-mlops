import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger

MAX_WORKERS = 8


class S3Sync:
    """Sync a local folder with an S3 prefix. Skips files whose size already matches."""

    def __init__(self, client=None):
        # boto3 clients are thread-safe, so one client is shared by the thread pool
        self.s3 = client or boto3.client(
            "s3", config=Config(retries={"max_attempts": 5, "mode": "standard"})
        )

    def sync_folder_to_s3(self, folder: Path, bucket: str, prefix: str) -> int:
        """Upload every file under folder to s3://bucket/prefix/... Returns files uploaded."""
        try:
            folder = Path(folder)
            if not folder.is_dir():
                raise FileNotFoundError(f"Folder does not exist: {folder}")

            files = [p for p in folder.rglob("*") if p.is_file()]
            prefix = prefix.strip("/")

            def upload(path: Path) -> int:
                key = f"{prefix}/{path.relative_to(folder).as_posix()}"
                if self._remote_size(bucket, key) == path.stat().st_size:
                    return 0
                self.s3.upload_file(str(path), bucket, key)
                return 1

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                uploaded = sum(pool.map(upload, files))

            logger.info(
                f"Synced {folder} to s3://{bucket}/{prefix}: {uploaded}/{len(files)} uploaded"
            )
            return uploaded
        except Exception as e:
            logger.error(f"Sync to s3 failed: {e}")
            raise NetworkSecurityException(e, sys) from e

    def sync_folder_from_s3(self, folder: Path, bucket: str, prefix: str) -> int:
        """Download every object under s3://bucket/prefix into folder. Returns files downloaded."""
        try:
            folder = Path(folder).resolve()
            prefix = prefix.strip("/")
            objects = []
            # fetches all files from s3 bucket
            paginator = self.s3.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
                objects.extend(o for o in page.get("Contents", []) if not o["Key"].endswith("/"))

            def download(obj: dict) -> int:
                target = (folder / obj["Key"][len(prefix) + 1 :]).resolve()
                if not target.is_relative_to(folder):  # key like "../x" must not escape folder
                    raise ValueError(f"Unsafe S3 key: {obj['Key']}")
                if target.exists() and target.stat().st_size == obj["Size"]:
                    return 0
                target.parent.mkdir(parents=True, exist_ok=True)
                self.s3.download_file(bucket, obj["Key"], str(target))
                return 1

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                downloaded = sum(pool.map(download, objects))

            logger.info(
                f"Synced s3://{bucket}/{prefix} to {folder}: {downloaded}/{len(objects)} downloaded"
            )
            return downloaded
        except Exception as e:
            logger.error(f"Sync from s3 failed: {e}")
            raise NetworkSecurityException(e, sys) from e

    def _remote_size(self, bucket: str, key: str) -> int | None:
        try:
            return self.s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
