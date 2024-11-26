import datetime
import json
import logging
import os
import sys
import tempfile
from io import BytesIO
from typing import BinaryIO, Protocol, overload

import sentry_sdk
import sentry_sdk.scope
import zstandard
from minio import Minio
from minio.credentials import (
    ChainedProvider,
    EnvAWSProvider,
    EnvMinioProvider,
    IamAwsProvider,
)
from minio.deleteobjects import DeleteObject
from minio.error import MinioException, S3Error
from urllib3.response import HTTPResponse

from shared.storage.base import BaseStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

log = logging.getLogger(__name__)


class Readable(Protocol):
    def read(self, size: int = -1) -> bytes: ...


class GetObjectToFileResponse(Protocol):
    bucket_name: str
    object_name: str
    last_modified: datetime.datetime | None
    etag: str
    size: int
    content_type: str | None
    metadata: dict[str, str]
    version_id: str | None


# Service class for interfacing with codecov's underlying storage layer, minio
class MinioStorageService(BaseStorageService):
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
        access_key: str = None,
        secret_key: str = None,
        verify_ssl: bool = False,
        iam_auth: bool = False,
        iam_endpoint: str = None,
        region: str = None,
    ):
        """
        Initialize the minio client

        `iam_auth` adds support for IAM base authentication in a fallback pattern.
        The following will be checked in order:

        * EC2 metadata -- a custom endpoint can be provided, default is None.
        * Minio env vars, specifically MINIO_ACCESS_KEY and MINIO_SECRET_KEY
        * AWS env vars, specifically AWS_ACCESS_KEY and AWS_SECRECT_KEY

        to support backward compatibility, the iam_auth setting should be used
        in the installation configuration

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
            )
        return Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            secure=verify_ssl,
            region=region,
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
        bucket_name: str,
        path: str,
        data: BinaryIO,
        reduced_redundancy: bool = False,
        *,
        is_already_gzipped: bool = False,  # deprecated
        is_compressed: bool = False,
        compression_type: str = "zstd",
    ):
        if is_already_gzipped:
            log.warning(
                "is_already_gzipped is deprecated and will be removed in a future version, instead compress using zstd and use the is_already_zstd_compressed argument"
            )
            with sentry_sdk.new_scope() as scope:
                scope.set_extra("bucket_name", bucket_name)
                scope.set_extra("path", path)
                sentry_sdk.capture_message("is_already_gzipped passed with True")
            is_compressed = True
            compression_type = "gzip"

        if isinstance(data, str):
            log.warning(
                "passing data as a str to write_file is deprecated and will be removed in a future version, instead pass an object compliant with the BinaryIO type"
            )
            with sentry_sdk.new_scope() as scope:
                scope.set_extra("bucket_name", bucket_name)
                scope.set_extra("path", path)
                sentry_sdk.capture_message("write_file data argument passed as str")

            data = BytesIO(data.encode())

        if not is_compressed:
            cctx = zstandard.ZstdCompressor()
            reader: zstandard.ZstdCompressionReader = cctx.stream_reader(data)
            _, filepath = tempfile.mkstemp()
            with open(filepath, "wb") as f:
                while chunk := reader.read(16384):
                    f.write(chunk)
            data = open(filepath, "rb")

        try:
            out_size = data.seek(0, os.SEEK_END)
            data.seek(0)

            if compression_type == "gzip":
                content_encoding = "gzip"
            elif compression_type == "zstd":
                content_encoding = "zstd"

            headers = {"Content-Encoding": content_encoding}

            if reduced_redundancy:
                headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"

            self.minio_client.put_object(
                bucket_name,
                path,
                data,
                out_size,
                metadata=headers,
                content_type="text/plain",
            )
            return True

        except MinioException:
            raise
        finally:
            if not is_compressed:
                data.close()
                os.unlink(filepath)

    @overload
    def read_file(
        self, bucket_name: str, path: str, file_obj: None = None
    ) -> bytes: ...

    @overload
    def read_file(self, bucket_name: str, path: str, file_obj: str) -> None: ...

    def read_file(self, bucket_name, path, file_obj=None) -> bytes | None:
        try:
            headers = {"Accept-Encoding": "gzip, zstd"}
            if file_obj:
                _, tmpfilepath = tempfile.mkstemp()
                to_file_response: GetObjectToFileResponse = (
                    self.minio_client.fget_object(
                        bucket_name, path, tmpfilepath, request_headers=headers
                    )
                )
                data = open(tmpfilepath, "rb")
                content_encoding = to_file_response.metadata.get(
                    "Content-Encoding", None
                )
            else:
                response: HTTPResponse = self.minio_client.get_object(
                    bucket_name, path, request_headers=headers
                )
                data = response
                content_encoding = response.headers.get("Content-Encoding", None)

            reader: Readable | None = None
            if content_encoding == "gzip":
                # HTTPResponse automatically decodes gzipped data for us
                # minio_client.fget_object uses HTTPResponse under the hood,
                # so this applies to both get_object and fget_object
                reader = data
            elif content_encoding == "zstd":
                # we have to manually decompress zstandard compressed data
                cctx = zstandard.ZstdDecompressor()
                reader = cctx.stream_reader(data)
            else:
                with sentry_sdk.new_scope() as scope:
                    scope.set_extra("bucket_name", bucket_name)
                    scope.set_extra("path", path)
                    raise ValueError("Blob does not have Content-Encoding set")

            if file_obj:
                while chunk := reader.read(16384):
                    file_obj.write(chunk)
                return None
            else:
                res = BytesIO()
                while chunk := reader.read(16384):
                    res.write(chunk)
                return res.getvalue()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotInStorageError(
                    f"File {path} does not exist in {bucket_name}"
                )
            raise e
        except MinioException:
            raise
        finally:
            if file_obj:
                data.close()
                os.unlink(tmpfilepath)

    """
        Deletes file url in specified bucket.
        Return true on successful
        deletion, returns a ResponseError otherwise.
    """

    def delete_file(self, bucket_name, url):
        try:
            # delete a file given a bucket name and a url
            self.minio_client.remove_object(bucket_name, url)
            return True
        except MinioException:
            raise

    def delete_files(self, bucket_name, urls=[]):
        try:
            for del_err in self.minio_client.remove_objects(
                bucket_name, [DeleteObject(url) for url in urls]
            ):
                print("Deletion error: {}".format(del_err))
            return [True] * len(urls)
        except MinioException:
            raise

    def list_folder_contents(self, bucket_name, prefix=None, recursive=True):
        return (
            self.object_to_dict(b)
            for b in self.minio_client.list_objects(bucket_name, prefix, recursive)
        )

    def object_to_dict(self, obj):
        return {"name": obj.object_name, "size": obj.size}

    # TODO remove this function -- just using it for output during testing.
    def write(self, string, silence=False):
        if not silence:
            sys.stdout.write((string or "") + "\n")
