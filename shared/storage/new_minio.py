import gzip
import importlib.metadata
import json
import logging
from io import BytesIO
from typing import IO, BinaryIO, Tuple, cast, overload

import zstandard
from minio import Minio
from minio.credentials.providers import (
    ChainedProvider,
    EnvAWSProvider,
    EnvMinioProvider,
    IamAwsProvider,
)
from minio.error import MinioException, S3Error
from minio.helpers import ObjectWriteResult
from urllib3 import HTTPResponse

from shared.storage.base import CHUNK_SIZE, PART_SIZE, BaseStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

log = logging.getLogger(__name__)


class GZipStreamReader:
    def __init__(self, fileobj: IO[bytes]):
        self.data = fileobj

    def read(self, size: int = -1, /) -> bytes:
        curr_data = self.data.read(size)

        if not curr_data:
            return b""

        return gzip.compress(curr_data)


def zstd_decoded_by_default() -> bool:
    try:
        version = importlib.metadata.version("urllib3")
    except importlib.metadata.PackageNotFoundError:
        return False

    if version < "2.0.0":
        return False

    distribution = importlib.metadata.metadata("urllib3")
    if requires_dist := distribution.get_all("Requires-Dist"):
        for req in requires_dist:
            if "[zstd]" in req:
                return True

    return False


# Service class for interfacing with codecov's underlying storage layer, minio
class NewMinioStorageService(BaseStorageService):
    def __init__(self, minio_config):
        self.zstd_default = zstd_decoded_by_default()

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
        data: IO[bytes] | str | bytes,
        reduced_redundancy: bool = False,
        *,
        is_already_gzipped: bool = False,  # deprecated
        is_compressed: bool = False,
        compression_type: str | None = "zstd",
    ) -> ObjectWriteResult:
        if isinstance(data, str):
            data = BytesIO(data.encode())
        elif isinstance(data, (bytes, bytearray, memoryview)):
            data = BytesIO(data)

        if is_already_gzipped:
            is_compressed = True
            compression_type = "gzip"

        if is_compressed:
            result = data
        else:
            if compression_type == "zstd":
                cctx = zstandard.ZstdCompressor()
                result = cctx.stream_reader(data)

            elif compression_type == "gzip":
                result = GZipStreamReader(data)

            else:
                result = data

        headers: dict[str, str | list[str] | Tuple[str]] = {}

        if compression_type:
            headers["Content-Encoding"] = compression_type

        if reduced_redundancy:
            headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"

        # it's safe to do a BinaryIO cast here because we know that put_object only uses a function of the shape:
        # read(self, size: int = -1, /) -> bytes
        # GZipStreamReader implements this (we did it ourselves)
        # ZstdCompressionReader implements read(): https://github.com/indygreg/python-zstandard/blob/12a80fac558820adf43e6f16206120685b9eb880/zstandard/__init__.pyi#L233C5-L233C49
        # BytesIO implements read(): https://docs.python.org/3/library/io.html#io.BufferedReader.read
        # IO[bytes] implements read(): https://github.com/python/cpython/blob/3.13/Lib/typing.py#L3502

        return self.minio_client.put_object(
            bucket_name,
            path,
            cast(BinaryIO, result),
            -1,
            metadata=headers,
            content_type="text/plain",
            part_size=PART_SIZE,
        )

    @overload
    def read_file(
        self, bucket_name: str, path: str, file_obj: None = None
    ) -> bytes: ...

    @overload
    def read_file(self, bucket_name: str, path: str, file_obj: IO[bytes]) -> None: ...

    def read_file(
        self, bucket_name: str, path: str, file_obj: IO[bytes] | None = None
    ) -> bytes | None:
        headers: dict[str, str | list[str] | Tuple[str]] = {
            "Accept-Encoding": "gzip, zstd"
        }
        try:
            response = cast(
                HTTPResponse,
                self.minio_client.get_object(  # this returns an HTTPResponse
                    bucket_name, path, request_headers=headers
                ),
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotInStorageError(
                    f"File {path} does not exist in {bucket_name}"
                )
            raise e
        if response.headers:
            content_encoding = response.headers.get("Content-Encoding", None)
            if not self.zstd_default and content_encoding == "zstd":
                # we have to manually decompress zstandard compressed data
                cctx = zstandard.ZstdDecompressor()
                # if the object passed to this has a read method then that's
                # all this object will ever need, since it will just call read
                # and get the bytes object resulting from it then compress that
                # HTTPResponse
                reader = cctx.stream_reader(cast(IO[bytes], response))
            else:
                reader = response
        else:
            reader = response

        if file_obj:
            file_obj.seek(0)
            while chunk := reader.read(CHUNK_SIZE):
                file_obj.write(chunk)
            response.close()
            response.release_conn()
            return None
        else:
            res = BytesIO()
            while chunk := reader.read(CHUNK_SIZE):
                res.write(chunk)
            response.close()
            response.release_conn()
            return res.getvalue()

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
