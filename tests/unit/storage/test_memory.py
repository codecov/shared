import tempfile
from uuid import uuid4

import pytest

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.memory import MemoryStorageService

BUCKET_NAME = "archivetest"


def make_storage() -> MemoryStorageService:
    return MemoryStorageService({})


def ensure_bucket(storage: MemoryStorageService):
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
