import gzip
from io import BytesIO

import pytest

from shared.storage.aws import AWSStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from tests.base import BaseTestCase

aws_config = {
    "resource": "s3",
    "aws_access_key_id": "testv5u6c7xxo7pom09w",
    "aws_secret_access_key": "aaaaaaibbbaaaaaaaaa1aaaEHaaaQbbboc7mpaaa",
    "region_name": "us-east-1",
}


class TestAWSStorageService(BaseTestCase):
    def test_create_bucket(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        bucket_name = "felipearchivetest"
        res = storage.create_root_storage(bucket_name=bucket_name)
        assert res["name"] == "felipearchivetest"

    def test_create_bucket_at_region(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        bucket_name = "felipearchivetestw"
        res = storage.create_root_storage(bucket_name=bucket_name, region="us-west-1")
        assert res["name"] == "felipearchivetestw"

    def test_create_bucket_already_exists(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        bucket_name = "felipearchivetest"
        with pytest.raises(BucketAlreadyExistsError):
            storage.create_root_storage(bucket_name=bucket_name)

    def test_create_bucket_already_exists_at_region(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        bucket_name = "felipearchivetestw"
        with pytest.raises(BucketAlreadyExistsError):
            storage.create_root_storage(bucket_name=bucket_name, region="us-west-1")

    def test_write_then_read_file(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "felipearchivetest"
        writing_result = storage.write_file(
            bucket_name=bucket_name, path=path, data=data
        )
        assert writing_result
        reading_result = storage.read_file(bucket_name=bucket_name, path=path)
        assert reading_result.decode() == data

    def test_write_then_read_gzipped_file(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        path = "test_write_then_read_gzipped_file/result"
        data = "lorem ipsum dolor test_write_then_read_gzipped_file á"
        bucket_name = "felipearchivetest"
        out = BytesIO()
        with gzip.GzipFile(fileobj=out, mode="w", compresslevel=9) as gz:
            encoded_data = data.encode()
            gz.write(encoded_data)
        data_to_write = out.getvalue()
        writing_result = storage.write_file(
            bucket_name=bucket_name, path=path, data=data_to_write
        )
        assert writing_result
        reading_result = storage.read_file(bucket_name=bucket_name, path=path)
        assert reading_result.decode() == data

    def test_write_then_read_reduced_redundancy_file(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        path = "test_write_then_read_reduced_redundancy_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "felipearchivetest"
        writing_result = storage.write_file(
            bucket_name=bucket_name, path=path, data=data, reduced_redundancy=True
        )
        assert writing_result
        reading_result = storage.read_file(bucket_name=bucket_name, path=path)
        assert reading_result.decode() == data

    def test_delete_file(self, codecov_vcr):
        storage = AWSStorageService(aws_config)
        path = "test_delete_file/result2"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "felipearchivetest"
        writing_result = storage.write_file(
            bucket_name=bucket_name, path=path, data=data
        )
        assert writing_result
        delete_result = storage.delete_file(bucket_name=bucket_name, path=path)
        assert delete_result
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name=bucket_name, path=path)
