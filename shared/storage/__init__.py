from shared.config import get_config
from shared.rollouts.features import USE_NEW_MINIO
from shared.storage.aws import AWSStorageService
from shared.storage.base import BaseStorageService
from shared.storage.fallback import StorageWithFallbackService
from shared.storage.gcp import GCPStorageService
from shared.storage.minio import MinioStorageService
from shared.storage.new_minio import NewMinioStorageService


def get_appropriate_storage_service(
    repoid: int | None = None,
) -> BaseStorageService:
    chosen_storage: str = get_config("services", "chosen_storage", default="minio")  # type: ignore
    return _get_appropriate_storage_service_given_storage(chosen_storage, repoid)


def _get_appropriate_storage_service_given_storage(
    chosen_storage: str, repoid: int | None
) -> BaseStorageService:
    if chosen_storage == "gcp":
        gcp_config = get_config("services", "gcp", default={})
        return GCPStorageService(gcp_config)
    elif chosen_storage == "aws":
        aws_config = get_config("services", "aws", default={})
        return AWSStorageService(aws_config)
    elif chosen_storage == "gcp_with_fallback":
        gcp_config = get_config("services", "gcp", default={})
        gcp_service = GCPStorageService(gcp_config)
        aws_config = get_config("services", "aws", default={})
        aws_service = AWSStorageService(aws_config)
        return StorageWithFallbackService(gcp_service, aws_service)
    else:
        minio_config = get_config("services", "minio", default={})
        if repoid and USE_NEW_MINIO.check_value(repoid, default=False):
            return NewMinioStorageService(minio_config)
        return MinioStorageService(minio_config)
