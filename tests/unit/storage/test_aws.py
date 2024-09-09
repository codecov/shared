import gzip
import tempfile
from io import BytesIO
from uuid import uuid4

import pytest

from shared.storage.aws import AWSStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

BUCKET_NAME = "archivetest"


def make_storage() -> AWSStorageService:
    return AWSStorageService(
        {
            "resource": "s3",
            "endpoint_url": "http://minio:9000",
            "aws_access_key_id": "codecov-default-key",
            "aws_secret_access_key": "codecov-default-secret",
        }
    )


def ensure_bucket(storage: AWSStorageService):
    try:
        storage.create_root_storage(BUCKET_NAME)
    except Exception:
        pass


def test_create_bucket():
    storage = make_storage()
    bucket_name = uuid4().hex

    res = storage.create_root_storage(bucket_name, region="")
    assert res == {"name": bucket_name}


def test_create_bucket_at_region():
    storage = make_storage()
    bucket_name = uuid4().hex

    res = storage.create_root_storage(bucket_name, region="us-west-1")
    assert res == {"name": bucket_name}


def test_create_bucket_already_exists():
    storage = make_storage()
    bucket_name = uuid4().hex

    storage.create_root_storage(bucket_name)
    with pytest.raises(BucketAlreadyExistsError):
        storage.create_root_storage(bucket_name)


def test_create_bucket_already_exists_at_region():
    storage = make_storage()
    bucket_name = uuid4().hex

    storage.create_root_storage(bucket_name, region="us-west-1")
    with pytest.raises(BucketAlreadyExistsError):
        storage.create_root_storage(bucket_name, region="us-west-1")


def test_write_then_read_file():
    storage = make_storage()
    path = f"test_write_then_read_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file á"

    ensure_bucket(storage)
    writing_result = storage.write_file(BUCKET_NAME, path, data)
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


def test_write_then_read_file_obj():
    storage = make_storage()
    path = f"test_write_then_read_file_obj/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file_obj á"

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


def test_read_file_does_not_exist():
    storage = make_storage()
    path = f"test_read_file_does_not_exist/{uuid4().hex}"

    ensure_bucket(storage)
    with pytest.raises(FileNotInStorageError):
        storage.read_file(BUCKET_NAME, path)


def test_write_then_read_gzipped_file():
    storage = make_storage()
    path = f"test_write_then_read_gzipped_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_gzipped_file á"

    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w", compresslevel=9) as gz:
        encoded_data = data.encode()
        gz.write(encoded_data)
    data_to_write = out.getvalue()

    writing_result = storage.write_file(
        BUCKET_NAME, path, data_to_write, is_already_gzipped=True
    )
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


def test_write_then_read_reduced_redundancy_file():
    storage = make_storage()
    path = f"test_write_then_read_reduced_redundancy_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_reduced_redundancy_file á"

    writing_result = storage.write_file(
        BUCKET_NAME, path, data, reduced_redundancy=True
    )
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


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
    assert results_1 == [
        {"name": f"{path}{path_1}", "size": 38},
        {"name": f"{path}{path_2}", "size": 40},
        {"name": f"{path}{path_3}", "size": 42},
        {"name": f"{path}{path_4}", "size": 47},
        {"name": f"{path}{path_5}", "size": 49},
        {"name": f"{path}{path_6}", "size": 51},
    ]

    results_2 = sorted(
        storage.list_folder_contents(BUCKET_NAME, f"{path}/x1"),
        key=lambda x: x["name"],
    )
    assert results_2 == [
        {"name": f"{path}{path_4}", "size": 47},
        {"name": f"{path}{path_5}", "size": 49},
        {"name": f"{path}{path_6}", "size": 51},
    ]
