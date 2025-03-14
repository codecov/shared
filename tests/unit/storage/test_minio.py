import gzip
import tempfile
from io import BytesIO
from uuid import uuid4

import pytest
import zstandard

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.minio import MinioStorageService, zstd_decoded_by_default

BUCKET_NAME = "archivetest"


def test_zstd_by_default():
    assert not zstd_decoded_by_default()


def test_gzip_stream_compression():
    data = "lorem ipsum dolor test_write_then_read_file á"

    split_data = [data[i : i + 5] for i in range(0, len(data), 5)]

    compressed_pieces: list[bytes] = [
        gzip.compress(piece.encode()) for piece in split_data
    ]

    assert gzip.decompress(b"".join(compressed_pieces)) == data.encode()


def make_storage() -> MinioStorageService:
    return MinioStorageService(
        {
            "access_key_id": "codecov-default-key",
            "secret_access_key": "codecov-default-secret",
            "verify_ssl": False,
            "host": "minio",
            "port": "9000",
            "iam_auth": False,
            "iam_endpoint": None,
        }
    )


def ensure_bucket(storage: MinioStorageService):
    try:
        storage.create_root_storage(BUCKET_NAME)
    except Exception:
        pass


def test_create_bucket():
    storage = make_storage()
    bucket_name = uuid4().hex

    res = storage.create_root_storage(bucket_name, region="")
    assert res == {"name": bucket_name}


def test_create_bucket_already_exists():
    storage = make_storage()
    bucket_name = uuid4().hex

    storage.create_root_storage(bucket_name)
    with pytest.raises(BucketAlreadyExistsError):
        storage.create_root_storage(bucket_name)


def test_write_then_read_file():
    storage = make_storage()
    path = f"test_write_then_read_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file á"

    ensure_bucket(storage)
    writing_result = storage.write_file(BUCKET_NAME, path, data)
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


def test_write_then_read_file_already_gzipped():
    storage = make_storage()
    path = f"test_write_then_read_file_already_gzipped/{uuid4().hex}"
    data = BytesIO(
        gzip.compress("lorem ipsum dolor test_write_then_read_file á".encode())
    )

    ensure_bucket(storage)
    writing_result = storage.write_file(
        BUCKET_NAME, path, data, is_already_gzipped=True
    )
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == "lorem ipsum dolor test_write_then_read_file á"


def test_write_then_read_file_already_zstd():
    storage = make_storage()
    path = f"test_write_then_read_file_already_zstd/{uuid4().hex}"
    data = BytesIO(
        zstandard.compress("lorem ipsum dolor test_write_then_read_file á".encode())
    )

    ensure_bucket(storage)
    writing_result = storage.write_file(
        BUCKET_NAME, path, data, compression_type="zstd", is_compressed=True
    )
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == "lorem ipsum dolor test_write_then_read_file á"


def test_write_then_read_file_obj():
    storage = make_storage()
    path = f"test_write_then_read_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file á"

    ensure_bucket(storage)

    _, local_path = tempfile.mkstemp()
    with open(local_path, "w") as f:
        f.write(data)
    with open(local_path, "rb") as f:
        writing_result = storage.write_file(BUCKET_NAME, path, f)
    assert writing_result

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == data


def test_write_then_read_file_obj_gzip():
    storage = make_storage()
    path = f"test_write_then_read_file_gzip/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file á"

    ensure_bucket(storage)

    _, local_path = tempfile.mkstemp()
    with open(local_path, "w") as f:
        f.write(data)
    with open(local_path, "rb") as f:
        writing_result = storage.write_file(
            BUCKET_NAME, path, f, compression_type="gzip"
        )
    assert writing_result

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == data


def test_write_then_read_file_obj_no_compression():
    storage = make_storage()
    path = f"test_write_then_read_file_no_compression/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file á"

    ensure_bucket(storage)

    _, local_path = tempfile.mkstemp()
    with open(local_path, "w") as f:
        f.write(data)
    with open(local_path, "rb") as f:
        writing_result = storage.write_file(BUCKET_NAME, path, f, compression_type=None)
    assert writing_result

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == data


def test_write_then_read_file_obj_x_gzip():
    storage = make_storage()
    path = f"test_write_then_read_file_obj_x_gzip/{uuid4().hex}"
    compressed = gzip.compress("lorem ipsum dolor test_write_then_read_file á".encode())
    outsize = len(compressed)
    data = BytesIO(compressed)

    ensure_bucket(storage)

    headers = {"Content-Encoding": "gzip"}
    storage.minio_client.put_object(
        BUCKET_NAME,
        path,
        data,
        content_type="application/x-gzip",
        metadata=headers,
        length=outsize,
    )

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == "lorem ipsum dolor test_write_then_read_file á"


def test_write_then_read_file_obj_already_gzipped():
    storage = make_storage()
    path = f"test_write_then_read_file_obj_already_gzipped/{uuid4().hex}"
    data = BytesIO(
        gzip.compress("lorem ipsum dolor test_write_then_read_file á".encode())
    )

    ensure_bucket(storage)

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        f.write(data.getvalue())
    with open(local_path, "rb") as f:
        writing_result = storage.write_file(
            BUCKET_NAME, path, f, is_already_gzipped=True
        )
    assert writing_result

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == "lorem ipsum dolor test_write_then_read_file á"


def test_write_then_read_file_obj_already_zstd():
    storage = make_storage()
    path = f"test_write_then_read_file_obj_already_zstd/{uuid4().hex}"
    data = BytesIO(
        zstandard.compress("lorem ipsum dolor test_write_then_read_file á".encode())
    )

    ensure_bucket(storage)

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        f.write(data.getvalue())
    with open(local_path, "rb") as f:
        writing_result = storage.write_file(
            BUCKET_NAME, path, f, is_compressed=True, compression_type="zstd"
        )
    assert writing_result

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == "lorem ipsum dolor test_write_then_read_file á"


def test_read_file_does_not_exist():
    storage = make_storage()
    path = f"test_read_file_does_not_exist/{uuid4().hex}"

    ensure_bucket(storage)
    with pytest.raises(FileNotInStorageError):
        storage.read_file(BUCKET_NAME, path)


def test_write_then_delete_file():
    storage = make_storage()
    path = f"test_write_then_delete_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_delete_file á"

    ensure_bucket(storage)
    writing_result = storage.write_file(BUCKET_NAME, path, data)
    assert writing_result

    deletion_result = storage.delete_file(BUCKET_NAME, path)
    assert deletion_result is True
    with pytest.raises(FileNotInStorageError):
        storage.read_file(BUCKET_NAME, path)


def test_delete_file_doesnt_exist():
    storage = make_storage()
    path = f"test_delete_file_doesnt_exist/{uuid4().hex}"

    ensure_bucket(storage)
    try:
        storage.delete_file(BUCKET_NAME, path)
    except FileNotInStorageError:
        pass


def test_minio_without_ports():
    minio_no_ports_config = {
        "access_key_id": "hodor",
        "secret_access_key": "haha",
        "verify_ssl": False,
        "host": "cute_url_no_ports",
        "iam_auth": True,
        "iam_endpoint": None,
    }
    storage = MinioStorageService(minio_no_ports_config)
    assert storage.minio_config == minio_no_ports_config
    assert storage.minio_client._base_url._url.port is None


def test_minio_with_ports():
    minio_no_ports_config = {
        "access_key_id": "hodor",
        "secret_access_key": "haha",
        "verify_ssl": False,
        "host": "cute_url_no_ports",
        "port": "9000",
        "iam_auth": True,
        "iam_endpoint": None,
    }
    storage = MinioStorageService(minio_no_ports_config)
    assert storage.minio_config == minio_no_ports_config
    assert storage.minio_client._base_url.region is None


def test_minio_with_region():
    minio_no_ports_config = {
        "access_key_id": "hodor",
        "secret_access_key": "haha",
        "verify_ssl": False,
        "host": "cute_url_no_ports",
        "port": "9000",
        "iam_auth": True,
        "iam_endpoint": None,
        "region": "example",
    }
    storage = MinioStorageService(minio_no_ports_config)
    assert storage.minio_config == minio_no_ports_config
    assert storage.minio_client._base_url.region == "example"
