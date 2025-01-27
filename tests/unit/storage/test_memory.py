import tempfile

import pytest

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.memory import MemoryStorageService
from tests.base import BaseTestCase

minio_config = {
    "access_key_id": "codecov-default-key",
    "secret_access_key": "codecov-default-secret",
    "verify_ssl": False,
    "host": "minio",
    "port": "9000",
}


class TestMemoryStorageService(BaseTestCase):
    def test_create_bucket(self, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        bucket_name = "thiagoarchivetest"
        res = storage.create_root_storage(bucket_name, region="")
        assert res == {"name": "thiagoarchivetest"}

    def test_create_bucket_already_exists(self, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        bucket_name = "alreadyexists"
        storage.root_storage_created = True
        with pytest.raises(BucketAlreadyExistsError):
            storage.create_root_storage(bucket_name)

    def test_write_then_read_file(self, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "thiagoarchivetest"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == data

    def test_write_then_read_file_obj(self, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        _, local_path = tempfile.mkstemp()
        with open(local_path, "w") as f:
            f.write(data)
        f = open(local_path, "rb")
        bucket_name = "archivetest"
        writing_result = storage.write_file(bucket_name, path, f)
        assert writing_result

        _, local_path = tempfile.mkstemp()
        with open(local_path, "wb") as f:
            storage.read_file(bucket_name, path, file_obj=f)
        with open(local_path, "rb") as f:
            assert f.read().decode() == data

    def test_read_file_does_not_exist(self, request, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        path = f"{request.node.name}/does_not_exist.txt"
        bucket_name = "thiagoarchivetest"
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_write_then_delete_file(self, request, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        path = f"{request.node.name}/result.txt"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "thiagoarchivetest"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        deletion_result = storage.delete_file(bucket_name, path)
        assert deletion_result is True
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_delete_file_doesnt_exist(self, request, codecov_vcr):
        storage = MemoryStorageService(minio_config)
        path = f"{request.node.name}/result.txt"
        bucket_name = "thiagoarchivetest"
        with pytest.raises(FileNotInStorageError):
            storage.delete_file(bucket_name, path)
