import json
import logging
import os
from datetime import timedelta
from functools import lru_cache
from typing import IO, BinaryIO, Literal, overload

import certifi
import urllib3
from minio import Minio
from minio.credentials.providers import (
    ChainedProvider,
    EnvAWSProvider,
    EnvMinioProvider,
    IamAwsProvider,
)
from minio.error import MinioException, S3Error
from minio.helpers import ObjectWriteResult
from urllib3 import Retry
from urllib3.util import Timeout

from shared.storage.base import BaseStorageService, PresignedURLService
from shared.storage.compression import zstd_decoded_by_default
from shared.storage.exceptions import BucketAlreadyExistsError
from shared.storage.read import new_minio_read, old_minio_read
from shared.storage.write import new_minio_write, old_minio_write

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60


def init_minio_client(
    host: str,
    port: str | None,
    access_key: str | None,
    secret_key: str | None,
    verify_ssl: bool,
    iam_auth: bool,
    iam_endpoint: str | None,
    region: str | None,
):
    """
        Initialize the minio client

    `iam_auth` adds support for IAM base authentication in a fallback pattern.
        The following will be checked in order:

    * EC2 metadata -- a custom endpoint can be provided, default is None.
    * AWS env vars, specifically AWS_ACCESS_KEY and AWS_SECRECT_KEY
    * Minio env vars, specifically MINIO_ACCESS_KEY and MINIO_SECRET_KEY

    to support backward compatibility, the iam_auth setting should be used in the installation
        configuration

    Args:
        host (str): The address of the host where minio lives
        port (str): The port number (as str or int should be ok)
        access_key (str, optional): The access key (optional if IAM is being used)
        secret_key (str, optional): The secret key (optional if IAM is being used)
        verify_ssl (bool, optional): Whether minio should verify ssl
        iam_auth (bool, optional): Whether to use iam_auth
        iam_endpoint (str, optional): The endpoint to try to fetch EC2 metadata
        region (str, optional): The region of the host where minio lives
    """
    if port is not None:
        host = "{}:{}".format(host, port)

    http_client = urllib3.PoolManager(
        timeout=Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT),
        maxsize=10,
        cert_reqs="CERT_REQUIRED",
        ca_certs=os.environ.get("SSL_CERT_FILE") or certifi.where(),
        retries=Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[
                408,
                429,
                500,
                502,
                503,
                504,
            ],  # https://cloud.google.com/storage/docs/retry-strategy#python
        ),
    )
    if iam_auth:
        return Minio(
            host,
            secure=verify_ssl,
            region=region,
            credentials=ChainedProvider(
                providers=[
                    IamAwsProvider(custom_endpoint=iam_endpoint),
                    EnvMinioProvider(),
                    EnvAWSProvider(),
                ]
            ),
            http_client=http_client,
        )
    return Minio(
        host,
        access_key=access_key,
        secret_key=secret_key,
        secure=verify_ssl,
        region=region,
        http_client=http_client,
    )


@lru_cache(maxsize=None)
def get_cached_minio_client(
    host: str = "",
    port: str | None = None,
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
    verify_ssl: bool = False,
    iam_auth: bool = False,
    iam_endpoint: str | None = None,
    region: str | None = None,
    **kwargs,
):
    return init_minio_client(
        host,
        port,
        access_key_id,
        secret_access_key,
        verify_ssl,
        iam_auth,
        iam_endpoint,
        region,
    )


zstd_default = zstd_decoded_by_default()


# Service class for interfacing with codecov's underlying storage layer, minio
class MinioStorageService(BaseStorageService, PresignedURLService):
    def __init__(
        self,
        minio_config,
        new_mode: Literal["read", "write"] | None = None,
    ):
        self.minio_config = minio_config
        self.new_read = new_mode == "read" or new_mode == "write"
        self.new_write = new_mode == "write"

        log.debug("Connecting to minio with config %s", self.minio_config)

        self.minio_client = get_cached_minio_client(**self.minio_config)

        log.debug("Done setting up minio client")

    # writes the initial storage bucket to storage via minio.
    def create_root_storage(self, bucket_name="archive", region="us-east-1"):
        read_only_policy = {
            "Statement": [
                {
                    "Action": ["s3:GetObject"],
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                }
            ],
            "Version": "2012-10-17",
        }
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                log.debug(
                    "Making bucket on bucket %s on location %s", bucket_name, region
                )
                self.minio_client.make_bucket(bucket_name, location=region)
                log.debug("Setting policy")
                self.minio_client.set_bucket_policy(
                    bucket_name, json.dumps(read_only_policy)
                )
                log.debug("Done creating root storage")
                return {"name": bucket_name}
            else:
                raise BucketAlreadyExistsError(f"Bucket {bucket_name} already exists")
        # todo should only pass or raise
        except S3Error as e:
            if e.code == "BucketAlreadyOwnedByYou":
                raise BucketAlreadyExistsError(f"Bucket {bucket_name} already exists")
            elif e.code == "BucketAlreadyExists":
                pass
            raise
        except MinioException:
            raise

    # Writes a file to storage will gzip if not compressed already
    def write_file(
        self,
        bucket_name: str,
        path: str,
        data: IO[bytes] | str | bytes,
        reduced_redundancy: bool = False,
        *,
        is_already_gzipped: bool = False,  # deprecated
        is_compressed: bool = False,
        compression_type: str | None = "zstd",
    ) -> ObjectWriteResult | Literal[True]:
        if self.new_write:
            return new_minio_write(
                self.minio_client,
                bucket_name,
                path,
                data,
                reduced_redundancy,
                is_already_gzipped=is_already_gzipped,
                is_compressed=is_compressed,
                compression_type=compression_type,
            )
        else:
            return old_minio_write(
                self.minio_client,
                bucket_name,
                path,
                data,
                reduced_redundancy,
                is_already_gzipped=is_already_gzipped,
            )

    @overload
    def read_file(self, bucket_name: str, path: str) -> bytes: ...

    @overload
    def read_file(self, bucket_name: str, path: str, file_obj: BinaryIO) -> None: ...

    def read_file(
        self, bucket_name: str, path: str, file_obj: BinaryIO | None = None
    ) -> bytes | None:
        if self.new_read:
            return new_minio_read(
                self.minio_client,
                bucket_name,
                path,
                file_obj,
                zstd_default,
            )
        else:
            return old_minio_read(
                self.minio_client,
                bucket_name,
                path,
                file_obj,
            )

    """
        Deletes file url in specified bucket.
        Return true on successful
        deletion, returns a ResponseError otherwise.
    """

    def delete_file(self, bucket_name: str, path: str) -> bool:
        try:
            # delete a file given a bucket name and a path
            self.minio_client.remove_object(bucket_name, path)
            return True
        except MinioException:
            raise

    def create_presigned_put(self, bucket: str, path: str, expires: int) -> str:
        expires_td = timedelta(seconds=expires)
        return self.minio_client.presigned_put_object(bucket, path, expires_td)

    def create_presigned_get(self, bucket: str, path: str, expires: int) -> str:
        expires_td = timedelta(seconds=expires)
        return self.minio_client.presigned_get_object(bucket, path, expires_td)
