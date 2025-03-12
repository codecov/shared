from shared.storage import get_appropriate_storage_service
from shared.storage.minio import MinioStorageService

minio_config = {
    "access_key_id": "codecov-default-key",
    "secret_access_key": "codecov-default-secret",
    "verify_ssl": False,
    "host": "minio",
    "port": "9000",
    "iam_auth": False,
    "iam_endpoint": None,
}


class TestStorageInitialization(object):
    def test_get_appropriate_storage_service_minio(self, mock_configuration):
        mock_configuration.params["services"] = {
            "minio": minio_config,
        }
        res = get_appropriate_storage_service()
        assert isinstance(res, MinioStorageService)
        assert res.minio_config == minio_config
