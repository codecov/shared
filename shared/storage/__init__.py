from shared.config import get_config
from shared.storage.minio import MinioStorageService


def get_appropriate_storage_service(*_args, **_kwargs) -> MinioStorageService:
    minio_config = get_config("services", "minio", default={})
    return MinioStorageService(minio_config)
