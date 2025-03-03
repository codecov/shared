from io import BytesIO
from typing import IO, cast

import zstandard
from minio import Minio
from minio.error import MinioException, S3Error
from urllib3 import HTTPResponse

from shared.storage.base import CHUNK_SIZE
from shared.storage.exceptions import FileNotInStorageError


def old_minio_read(
    minio_client: Minio,
    bucket_name: str,
    path: str,
    file_obj: IO[bytes] | None = None,
) -> bytes | None:
    try:
        res = minio_client.get_object(bucket_name, path)
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
            raise FileNotInStorageError(f"File {path} does not exist in {bucket_name}")
        raise e
    except MinioException:
        raise


def new_minio_read(
    minio_client: Minio,
    bucket_name: str,
    path: str,
    file_obj: IO[bytes] | None = None,
    zstd_default: bool = False,
) -> bytes | None:
    try:
        response = cast(
            HTTPResponse,
            minio_client.get_object(bucket_name, path),
        )
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise FileNotInStorageError(f"File {path} does not exist in {bucket_name}")
        raise e
    reader = response
    if (
        response.headers
        and not zstd_default
        and response.headers.get("Content-Encoding") == "zstd"
    ):
        # we have to manually decompress zstandard compressed data
        cctx = zstandard.ZstdDecompressor()
        # if the object passed to this has a read method then that's
        # all this object will ever need, since it will just call read
        # and get the bytes object resulting from it then compress that
        # HTTPResponse
        reader = cctx.stream_reader(cast(IO[bytes], response))

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
