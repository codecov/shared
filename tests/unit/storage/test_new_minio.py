import gzip
import tempfile
from io import BytesIO
from uuid import uuid4

import pytest
import zstandard

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.new_minio import NewMinioStorageService, zstd_decoded_by_default

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


def make_storage() -> NewMinioStorageService:
    return NewMinioStorageService(
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


def ensure_bucket(storage: NewMinioStorageService):
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


def test_batch_delete_files():
    storage = make_storage()
    path = f"test_batch_delete_files/{uuid4().hex}"
    path_1 = f"{path}/result_1.txt"
    path_2 = f"{path}/result_2.txt"
    path_3 = f"{path}/result_3.txt"
    paths = [path_1, path_2, path_3]
    data = "lorem ipsum dolor test_batch_delete_files á"

    ensure_bucket(storage)
    storage.write_file(BUCKET_NAME, path_1, data)
    storage.write_file(BUCKET_NAME, path_3, data)

    deletion_result = storage.delete_files(BUCKET_NAME, paths)
    assert deletion_result == [True, True, True]
    for p in paths:
        with pytest.raises(FileNotInStorageError):
            storage.read_file(BUCKET_NAME, p)


def test_list_folder_contents():
    storage = make_storage()
    path = f"test_list_folder_contents/{uuid4().hex}"
    path_1 = "/result_1.txt"
    path_2 = "/result_2.txt"
    path_3 = "/result_3.txt"
    path_4 = "/x1/result_1.txt"
    path_5 = "/x1/result_2.txt"
    path_6 = "/x1/result_3.txt"
    all_paths = [path_1, path_2, path_3, path_4, path_5, path_6]

    ensure_bucket(storage)
    for i, p in enumerate(all_paths):
        data = f"Lorem ipsum on file {p} for {i * 'po'}"
        storage.write_file(BUCKET_NAME, f"{path}{p}", data)

    results_1 = sorted(
        storage.list_folder_contents(BUCKET_NAME, path),
        key=lambda x: x["name"],
    )
    # NOTE: the `size` here is actually the compressed (currently gzip) size
    assert results_1 == [
        {"name": f"{path}{path_1}", "size": 47},
        {"name": f"{path}{path_2}", "size": 49},
        {"name": f"{path}{path_3}", "size": 51},
        {"name": f"{path}{path_4}", "size": 56},
        {"name": f"{path}{path_5}", "size": 58},
        {"name": f"{path}{path_6}", "size": 60},
    ]

    results_2 = sorted(
        storage.list_folder_contents(BUCKET_NAME, f"{path}/x1"),
        key=lambda x: x["name"],
    )
    assert results_2 == [
        {"name": f"{path}{path_4}", "size": 56},
        {"name": f"{path}{path_5}", "size": 58},
        {"name": f"{path}{path_6}", "size": 60},
    ]


def test_minio_without_ports(mocker):
    mocked_minio_client = mocker.patch("shared.storage.new_minio.Minio")
    minio_no_ports_config = {
        "access_key_id": "hodor",
        "secret_access_key": "haha",
        "verify_ssl": False,
        "host": "cute_url_no_ports",
        "iam_auth": True,
        "iam_endpoint": None,
    }

    storage = NewMinioStorageService(minio_no_ports_config)
    assert storage.minio_config == minio_no_ports_config
    mocked_minio_client.assert_called_with(
        "cute_url_no_ports", credentials=mocker.ANY, secure=False, region=None
    )


def test_minio_with_ports(mocker):
    mocked_minio_client = mocker.patch("shared.storage.new_minio.Minio")
    minio_no_ports_config = {
        "access_key_id": "hodor",
        "secret_access_key": "haha",
        "verify_ssl": False,
        "host": "cute_url_no_ports",
        "port": "9000",
        "iam_auth": True,
        "iam_endpoint": None,
    }

    storage = NewMinioStorageService(minio_no_ports_config)
    assert storage.minio_config == minio_no_ports_config
    mocked_minio_client.assert_called_with(
        "cute_url_no_ports:9000", credentials=mocker.ANY, secure=False, region=None
    )


def test_minio_with_region(mocker):
    mocked_minio_client = mocker.patch("shared.storage.new_minio.Minio")
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

    storage = NewMinioStorageService(minio_no_ports_config)
    assert storage.minio_config == minio_no_ports_config
    mocked_minio_client.assert_called_with(
        "cute_url_no_ports:9000",
        credentials=mocker.ANY,
        secure=False,
        region="example",
    )
