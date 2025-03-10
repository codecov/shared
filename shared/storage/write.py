import gzip
import os
import shutil
import tempfile
from io import BytesIO
from typing import IO, BinaryIO, Literal, Tuple, cast

import sentry_sdk
import zstandard
from minio import Minio
from minio.error import MinioException
from minio.helpers import ObjectWriteResult

from shared.storage.base import PART_SIZE
from shared.storage.compression import GZipStreamReader


def old_minio_write(
    minio_client: Minio,
    bucket_name: str,
    path: str,
    data: IO[bytes] | str | bytes,
    reduced_redundancy: bool = False,
    *,
    is_already_gzipped: bool = False,  # deprecated
) -> Literal[True]:
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
        minio_client.put_object(
            bucket_name,
            path,
            out,
            out_size,
            metadata=headers,
            content_type="text/plain",
        )

        span = sentry_sdk.get_current_span()
        if span:
            span.set_data("size", out_size)

        return True

    except MinioException:
        raise


def new_minio_write(
    minio_client: Minio,
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

    write_result = minio_client.put_object(
        bucket_name,
        path,
        cast(BinaryIO, result),
        -1,
        metadata=headers,
        content_type="text/plain",
        part_size=PART_SIZE,
    )

    span = sentry_sdk.get_current_span()
    if span:
        span.set_data("size", result.tell())

    return write_result
