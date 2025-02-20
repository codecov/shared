from typing import Literal

from shared.config import get_config
from shared.rollouts.features import USE_NEW_MINIO
from shared.storage.aws import AWSStorageService
from shared.storage.base import BaseStorageService
from shared.storage.fallback import StorageWithFallbackService
from shared.storage.gcp import GCPStorageService
from shared.storage.minio import MinioStorageService
from shared.storage.new_minio import NewMinioStorageService

_storage_service_cache: dict[str, BaseStorageService] = {}


def get_appropriate_storage_service(
    repoid: int | None = None,
    force_minio=False,
) -> BaseStorageService:
    chosen_storage = "minio"
    if repoid and USE_NEW_MINIO.check_value(repoid, default=False):
        chosen_storage = "new_minio"

    if chosen_storage not in _storage_service_cache:
        _storage_service_cache[chosen_storage] = (
            _get_appropriate_storage_service_given_storage(chosen_storage)
        )

    return _storage_service_cache[chosen_storage]


def _get_appropriate_storage_service_given_storage(
    chosen_storage: Literal["minio", "new_minio"],
) -> BaseStorageService:
    if chosen_storage == "new_minio":
        minio_config = get_config("services", "minio", default={})
        return NewMinioStorageService(minio_config)
    elif chosen_storage == "minio":
        minio_config = get_config("services", "minio", default={})
        return MinioStorageService(minio_config)
