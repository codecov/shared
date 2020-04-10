from shared.storage.minio import MinioStorageService
from shared.storage.gcp import GCPStorageService
from shared.storage.aws import AWSStorageService
from shared.storage.fallback import StorageWithFallbackService
from shared.config import get_config


def get_appropriate_storage_service():
    chosen_storage = get_config("services", "chosen_storage", default="minio")
    return _get_appropriate_storage_service_given_storage(chosen_storage)


def _get_appropriate_storage_service_given_storage(chosen_storage):
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
        return MinioStorageService(minio_config)
