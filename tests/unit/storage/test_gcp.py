import gzip
import io
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from google.cloud import storage as google_storage
from google.resumable_media.common import DataCorruption

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.gcp import GCPStorageService
from tests.base import BaseTestCase

# DONT WORRY, this is generated for the purposes of validation, and is not the real
# one on which the code ran
fake_private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDCFqq2ygFh9UQU/6PoDJ6L9e4ovLPCHtlBt7vzDwyfwr3XGxln
0VbfycVLc6unJDVEGZ/PsFEuS9j1QmBTTEgvCLR6RGpfzmVuMO8wGVEO52pH73h9
rviojaheX/u3ZqaA0di9RKy8e3L+T0ka3QYgDx5wiOIUu1wGXCs6PhrtEwICBAEC
gYBu9jsi0eVROozSz5dmcZxUAzv7USiUcYrxX007SUpm0zzUY+kPpWLeWWEPaddF
VONCp//0XU8hNhoh0gedw7ZgUTG6jYVOdGlaV95LhgY6yXaQGoKSQNNTY+ZZVT61
zvHOlPynt3GZcaRJOlgf+3hBF5MCRoWKf+lDA5KiWkqOYQJBAMQp0HNVeTqz+E0O
6E0neqQDQb95thFmmCI7Kgg4PvkS5mz7iAbZa5pab3VuyfmvnVvYLWejOwuYSp0U
9N8QvUsCQQD9StWHaVNM4Lf5zJnB1+lJPTXQsmsuzWvF3HmBkMHYWdy84N/TdCZX
Cxve1LR37lM/Vijer0K77wAx2RAN/ppZAkB8+GwSh5+mxZKydyPaPN29p6nC6aLx
3DV2dpzmhD0ZDwmuk8GN+qc0YRNOzzJ/2UbHH9L/lvGqui8I6WLOi8nDAkEA9CYq
ewfdZ9LcytGz7QwPEeWVhvpm0HQV9moetFWVolYecqBP4QzNyokVnpeUOqhIQAwe
Z0FJEQ9VWsG+Df0noQJBALFjUUZEtv4x31gMlV24oiSWHxIRX4fEND/6LpjleDZ5
C/tY+lZIEO1Gg/FxSMB+hwwhwfSuE3WohZfEcSy+R48=
-----END RSA PRIVATE KEY-----"""

gcp_config = {
    "type": "service_account",
    "project_id": "genuine-polymer-165712",
    "private_key_id": "testu7gvpfyaasze2lboblawjb3032mbfisy9gpg",
    "private_key": fake_private_key,
    "client_email": "localstoragetester@genuine-polymer-165712.iam.gserviceaccount.com",
    "client_id": "110927033630051704865",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/localstoragetester%40genuine-polymer-165712.iam.gserviceaccount.com",
}


class TestGCPStorateService(BaseTestCase):
    def test_create_bucket(self, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        bucket_name = "testingarchive004"
        res = storage.create_root_storage(bucket_name)
        assert res["name"] == "testingarchive004"

    def test_create_bucket_already_exists(self, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        bucket_name = "testingarchive004"
        with pytest.raises(BucketAlreadyExistsError):
            storage.create_root_storage(bucket_name)

    def test_write_then_read_file(self, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "testingarchive02"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == data

    def test_write_then_read_file_obj(self, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = "test_write_then_read_file_obj/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        _, local_path = tempfile.mkstemp()
        with open(local_path, "w") as f:
            f.write(data)
        f = open(local_path, "rb")
        bucket_name = "testing"
        writing_result = storage.write_file(bucket_name, path, f)
        assert writing_result

        _, local_path = tempfile.mkstemp()
        with open(local_path, "wb") as f:
            storage.read_file(bucket_name, path, file_obj=f)
        with open(local_path, "rb") as f:
            assert f.read().decode() == data

    def test_manually_then_read_then_write_then_read_file(self, codecov_vcr):
        bucket_name = "testingarchive02"
        path = "test_manually_then_read_then_write_then_read_file/result01"
        storage = GCPStorageService(gcp_config)
        blob = storage.get_blob(bucket_name, path)
        blob.upload_from_string("some data around")
        assert storage.read_file(bucket_name, path).decode() == "some data around"
        blob.reload()
        assert blob.content_type == "text/plain"
        assert blob.content_encoding is None
        data = "lorem ipsum dolor test_write_then_read_file á"
        assert storage.write_file(bucket_name, path, data)
        assert storage.read_file(bucket_name, path).decode() == data
        blob = storage.get_blob(bucket_name, path)
        blob.reload()
        assert blob.content_type == "text/plain"
        assert blob.content_encoding == "gzip"

    def test_write_then_read_file_gzipped(self, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = "test_write_then_read_file/result"
        data = gzip.compress("lorem ipsum dolor test_write_then_read_file á".encode())
        bucket_name = "testingarchive02"
        writing_result = storage.write_file(
            bucket_name, path, data, is_already_gzipped=True
        )
        assert writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert (
            reading_result.decode() == "lorem ipsum dolor test_write_then_read_file á"
        )

    def test_write_then_append_then_read_file(self, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = "test_write_then_append_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        second_data = "mom, look at me, appending data"
        bucket_name = "testingarchive02"
        writing_result = storage.write_file(bucket_name, path, data)
        second_writing_result = storage.append_to_file(bucket_name, path, second_data)
        assert writing_result
        assert second_writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == "\n".join([data, second_data])

    def test_append_to_non_existing_file(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = f"{request.node.name}/result.txt"
        second_data = "mom, look at me, appending data"
        bucket_name = "testingarchive02"
        second_writing_result = storage.append_to_file(bucket_name, path, second_data)
        assert second_writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == second_data

    def test_read_file_does_not_exist(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = f"{request.node.name}/does_not_exist.txt"
        bucket_name = "testingarchive004"
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_read_file_application_gzip(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = f"gzipped_file/test_006.txt"
        bucket_name = "testingarchive004"
        content_to_upload = "content to write\nThis is crazy\nWhy does this work"
        bucket = storage.storage_client.get_bucket(bucket_name)
        blob = google_storage.Blob(path, bucket)
        with io.BytesIO() as f:
            with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9) as fgz:
                fgz.write(content_to_upload.encode())
            blob.content_encoding = "gzip"
            blob.upload_from_file(
                f, size=f.tell(), rewind=True, content_type="application/x-gzip"
            )
        content = storage.read_file(bucket_name, path)
        print(content)
        assert content.decode() == content_to_upload

    def test_write_then_delete_file(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = f"{request.node.name}/result.txt"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "testingarchive02"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        deletion_result = storage.delete_file(bucket_name, path)
        assert deletion_result is True
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_delete_file_doesnt_exist(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path = f"{request.node.name}/result.txt"
        bucket_name = "testingarchive004"
        with pytest.raises(FileNotInStorageError):
            storage.delete_file(bucket_name, path)

    def test_batch_delete_files(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path_1 = f"{request.node.name}/result_1.txt"
        path_2 = f"{request.node.name}/result_2.txt"
        path_3 = f"{request.node.name}/result_3.txt"
        paths = [path_1, path_2, path_3]
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "testingarchive004"
        storage.write_file(bucket_name, path_1, data)
        storage.write_file(bucket_name, path_3, data)
        deletion_result = storage.delete_files(bucket_name, paths)
        assert deletion_result == [True, False, True]
        for p in paths:
            with pytest.raises(FileNotInStorageError):
                storage.read_file(bucket_name, p)

    def test_list_folder_contents(self, request, codecov_vcr):
        storage = GCPStorageService(gcp_config)
        path_1 = f"thiago/{request.node.name}/result_1.txt"
        path_2 = f"thiago/{request.node.name}/result_2.txt"
        path_3 = f"thiago/{request.node.name}/result_3.txt"
        path_4 = f"thiago/{request.node.name}/f1/result_1.txt"
        path_5 = f"thiago/{request.node.name}/f1/result_2.txt"
        path_6 = f"thiago/{request.node.name}/f1/result_3.txt"
        all_paths = [path_1, path_2, path_3, path_4, path_5, path_6]
        bucket_name = "testingarchive004"
        for i, p in enumerate(all_paths):
            data = f"Lorem ipsum on file {p} for {i * 'po'}"
            storage.write_file(bucket_name, p, data)
        results_1 = list(
            storage.list_folder_contents(bucket_name, f"thiago/{request.node.name}")
        )
        expected_result_1 = [
            {"name": path_1, "size": 70},
            {"name": path_2, "size": 72},
            {"name": path_3, "size": 74},
            {"name": path_4, "size": 79},
            {"name": path_5, "size": 81},
            {"name": path_6, "size": 83},
        ]
        assert sorted(expected_result_1, key=lambda x: x["size"]) == sorted(
            results_1, key=lambda x: x["size"]
        )
        results_2 = list(
            storage.list_folder_contents(bucket_name, f"thiago/{request.node.name}/f1")
        )
        expected_result_2 = [
            {"name": path_4, "size": 79},
            {"name": path_5, "size": 81},
            {"name": path_6, "size": 83},
        ]
        assert sorted(expected_result_2, key=lambda x: x["size"]) == sorted(
            results_2, key=lambda x: x["size"]
        )

    @patch("shared.storage.gcp.storage")
    def test_read_file_retry_success(self, mock_storage):

        storage = GCPStorageService(gcp_config)
        mock_storage.Client.assert_called()
        mock_blob = MagicMock(
            name="fake_blob",
            download_as_bytes=MagicMock(
                side_effect=[
                    DataCorruption(response="checksum match failed"),
                    b"contents",
                ]
            ),
        )
        mock_storage.Blob.return_value = mock_blob
        response = storage.read_file("root_bucket", "path/to/blob", None)
        assert response == b"contents"

    @patch("shared.storage.gcp.storage")
    def test_read_file_retry_fail_twice(self, mock_storage):

        storage = GCPStorageService(gcp_config)
        mock_storage.Client.assert_called()
        mock_blob = MagicMock(
            name="fake_blob",
            download_as_bytes=MagicMock(
                side_effect=[
                    DataCorruption(response="checksum match failed"),
                    DataCorruption(response="checksum match failed"),
                ]
            ),
        )
        mock_storage.Blob.return_value = mock_blob
        with pytest.raises(DataCorruption):
            response = storage.read_file("root_bucket", "path/to/blob", None)
