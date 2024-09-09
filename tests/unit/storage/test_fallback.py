import tempfile
from uuid import uuid4

import pytest

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.fallback import StorageWithFallbackService

from .test_aws import make_storage as make_aws_storage
from .test_gcp import BUCKET_NAME, CREDENTIALS, IS_CI
from .test_gcp import make_storage as make_gcs_storage

pytestmark = pytest.mark.skipif(
    not IS_CI and not CREDENTIALS,
    reason="GCS credentials not available for local testing",
)


def make_storage() -> StorageWithFallbackService:
    gcp_storage = make_gcs_storage()
    aws_storage = make_aws_storage()
    return StorageWithFallbackService(gcp_storage, aws_storage)


def ensure_bucket(storage: StorageWithFallbackService):
    try:
        # The `fallback` here is aws / minio
        storage.fallback_service.create_root_storage(BUCKET_NAME)
    except Exception:
        pass


@pytest.mark.skip(reason="we currently have no way of cleaning up upstream buckets")
def test_create_bucket():
    storage = make_storage()
    bucket_name = uuid4().hex

    res = storage.create_root_storage(bucket_name, region="")
    assert res == {"name": bucket_name}


@pytest.mark.skip(reason="we currently have no way of cleaning up upstream buckets")
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


def test_read_file_does_not_exist_on_first_but_exists_on_second():
    storage = make_storage()
    path = f"test_read_file_does_not_exist_on_first_but_exists_on_second/{uuid4().hex}"
    data = "lorem ipsum dolor test_read_file_does_not_exist_on_first_but_exists_on_second á"

    storage.fallback_service.write_file(BUCKET_NAME, path, data)
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


def test_read_file_does_exist_on_first_but_not_exists_on_second():
    storage = make_storage()
    path = f"test_read_file_does_exist_on_first_but_not_exists_on_second/{uuid4().hex}"
    data = "lorem ipsum dolor test_read_file_does_exist_on_first_but_not_exists_on_second á"

    storage.main_service.write_file(BUCKET_NAME, path, data)
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


def test_delete_file_doesnt_exist():
    storage = make_storage()
    path = f"test_delete_file_doesnt_exist/{uuid4().hex}"

    ensure_bucket(storage)
    with pytest.raises(FileNotInStorageError):
        storage.delete_file(BUCKET_NAME, path)


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
    assert deletion_result == [True, False, True]
    for p in paths:
        with pytest.raises(FileNotInStorageError):
            storage.read_file(BUCKET_NAME, p)


@pytest.mark.skip(
    reason="the service account used for testing does not have bucket list permissions"
)
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
