import os
from minio import Minio


class ObjectStorage:
    """Object Storage class for managing files and artifacts."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        bucket: str | None = None,
        secure: bool = True,
    ):
        self.bucket = bucket
        endpoint = endpoint if endpoint else os.getenv("AWS_S3_ENDPOINT", None)
        access_key = access_key if access_key else os.getenv("AWS_ACCESS_KEY_ID", None)
        secret_key = secret_key if secret_key else os.getenv("AWS_SECRET_ACCESS_KEY", None)
        region = region if region else os.getenv("AWS_DEFAULT_REGION", "")
        bucket = bucket if bucket else os.getenv("AWS_S3_BUCKET", None)

        if not any((endpoint, access_key, secret_key)):
            msg = "Default variables must be set or specified in parameters of ObjectStorage."
            raise ObjectStorageError(msg)

        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            secure=secure
        )

    def upload_file(self, bucket: str, file_path: str, s3_path: str, *, meta: dict):
        """Upload file to S3

        Args:
            bucket: the bucket name
            file_path: the local file_path
            s3_path: the S3 path to save to

        Keyword Args:
            meta: the dictionary of metadata"""
        self.client.fput_object(
            bucket_name=bucket, file_path=file_path, object_name=s3_path, metadata=meta
        )

    def download_file(self, bucket: str, file_path: str, s3_path: str):
        """Download file from S3

        Args:
            bucket: the bucket name
            file_path: the local to save to
            s3_path: the S3 path of the file

        Keyword Args:
            meta: the dictionary of metadata"""
        try:
            self.client.fget_object(
                bucket_name=bucket, file_path=file_path, object_name=s3_path
            )
        except Exception:
            raise ObjectStorageError(
                "Could not retrieve file from S3. Please make sure remote path is correct."
            )


class ObjectStorageError(Exception):
    """Object Storage error."""
