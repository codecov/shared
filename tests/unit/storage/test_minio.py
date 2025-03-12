import os
import tempfile

import pytest

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.minio import MinioStorageService
from tests.base import BaseTestCase

minio_config = {
    "access_key_id": "codecov-default-key",
    "secret_access_key": "codecov-default-secret",
    "verify_ssl": False,
    "host": "minio",
    "port": "9000",
    "iam_auth": False,
    "iam_endpoint": None,
}


class TestMinioStorageService(BaseTestCase):
    def test_create_bucket(self, codecov_vcr):
        storage = MinioStorageService(minio_config)
        bucket_name = "archivetest"
        res = storage.create_root_storage(bucket_name, region="")
        assert res == {"name": "archivetest"}

    def test_create_bucket_already_exists(self, codecov_vcr):
        storage = MinioStorageService(minio_config)
        bucket_name = "alreadyexists"
        storage.create_root_storage(bucket_name)
        with pytest.raises(BucketAlreadyExistsError):
            storage.create_root_storage(bucket_name)

    def test_write_then_read_file(self, codecov_vcr):
        storage = MinioStorageService(minio_config)
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "archivetest"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == data

    def test_write_then_read_file_obj(self, codecov_vcr):
        storage = MinioStorageService(minio_config)
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
        storage = MinioStorageService(minio_config)
        path = f"{request.node.name}/does_not_exist.txt"
        bucket_name = "archivetest"
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_write_then_delete_file(self, request, codecov_vcr):
        storage = MinioStorageService(minio_config)
        path = f"{request.node.name}/result.txt"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "archivetest"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        deletion_result = storage.delete_file(bucket_name, path)
        assert deletion_result is True
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_delete_file_doesnt_exist(self, request, codecov_vcr):
        storage = MinioStorageService(minio_config)
        path = f"{request.node.name}/result.txt"
        bucket_name = "archivetest"
        storage.delete_file(bucket_name, path)

    """
    Since we cannot rely on `Chain` in the underlying implementation
    we cannot ''trick'' minio into using the IAM auth flow while testing,
    and therefore have to actually be running on an AWS instance.
    We can unskip this test after minio fixes their credential
    chain problem
    """

    @pytest.mark.skip(reason="Skipping because minio IAM is currently untestable.")
    def test_minio_with_iam_flow(self, codecov_vcr, mocker):
        mocker.patch.dict(
            os.environ,
            {
                "MINIO_ACCESS_KEY": "codecov-default-key",
                "MINIO_SECRET_KEY": "codecov-default-secret",
            },
        )
        minio_iam_config = {
            "access_key_id": "codecov-default-key",
            "secret_access_key": "codecov-default-secret",
            "verify_ssl": False,
            "host": "minio",
            "port": "9000",
            "iam_auth": True,
            "iam_endpoint": None,
        }
        bucket_name = "testminiowithiamflow"
        storage = MinioStorageService(minio_iam_config)
        storage.create_root_storage(bucket_name)
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == data

    def test_minio_without_ports(self):
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

    def test_minio_with_ports(self):
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

    def test_minio_with_region(self):
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
