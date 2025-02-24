import gzip
import json
import logging
import os
import shutil
import tempfile
from datetime import timedelta
from io import BytesIO
from typing import BinaryIO, overload

import certifi
import urllib3
from minio import Minio
from minio.credentials import (
    ChainedProvider,
    EnvAWSProvider,
    EnvMinioProvider,
    IamAwsProvider,
)
from minio.error import MinioException, S3Error
from urllib3 import Retry
from urllib3.util import Timeout

from shared.storage.base import CHUNK_SIZE, BaseStorageService, PresignedURLService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60


# Service class for interfacing with codecov's underlying storage layer, minio
class MinioStorageService(BaseStorageService, PresignedURLService):
    def __init__(self, minio_config):
        self.minio_config = minio_config
        log.debug("Connecting to minio with config %s", self.minio_config)

        self.minio_client = self.init_minio_client(
            self.minio_config["host"],
            self.minio_config.get("port"),
            self.minio_config["access_key_id"],
            self.minio_config["secret_access_key"],
            self.minio_config["verify_ssl"],
            self.minio_config.get("iam_auth", False),
            self.minio_config["iam_endpoint"],
            self.minio_config.get("region"),
        )
        log.debug("Done setting up minio client")

    def client(self):
        return self.minio_client if self.minio_client else None

    def init_minio_client(
        self,
        host: str,
        port: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        verify_ssl: bool = False,
        iam_auth: bool = False,
        iam_endpoint: str | None = None,
        region: str | None = None,
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
        bucket_name,
        path,
        data,
        reduced_redundancy=False,
        *,
        is_already_gzipped: bool = False,
    ):
        if isinstance(data, str):
            data = data.encode()

        out: BinaryIO
        if isinstance(data, bytes):
            if not is_already_gzipped:
                out = BytesIO()
                with gzip.GzipFile(fileobj=out, mode="w", compresslevel=9) as gz:
                    gz.write(data)
            else:
                out = BytesIO(data)

            # get file size
            out.seek(0, os.SEEK_END)
            out_size = out.tell()
        else:
            # data is already a file-like object
            if not is_already_gzipped:
                _, filename = tempfile.mkstemp()
                with gzip.open(filename, "wb") as f:
                    shutil.copyfileobj(data, f)
                out = open(filename, "rb")
            else:
                out = data

            out_size = os.stat(filename).st_size

        try:
            # reset pos for minio reading.
            out.seek(0)

            headers = {"Content-Encoding": "gzip"}
            if reduced_redundancy:
                headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"
            self.minio_client.put_object(
                bucket_name,
                path,
                out,
                out_size,
                metadata=headers,
                content_type="text/plain",
            )
            return True

        except MinioException:
            raise

    @overload
    def read_file(self, bucket_name: str, path: str) -> bytes: ...

    @overload
    def read_file(self, bucket_name: str, path: str, file_obj: BinaryIO) -> None: ...

    def read_file(
        self, bucket_name: str, path: str, file_obj: BinaryIO | None = None
    ) -> bytes | None:
        try:
            res = self.minio_client.get_object(bucket_name, path)
            if file_obj is None:
                data = BytesIO()
                for d in res.stream(CHUNK_SIZE):
                    data.write(d)
                data.seek(0)
                return data.getvalue()
            else:
                for d in res.stream(CHUNK_SIZE):
                    file_obj.write(d)
                return None
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotInStorageError(
                    f"File {path} does not exist in {bucket_name}"
                )
            raise e
        except MinioException:
            raise

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
