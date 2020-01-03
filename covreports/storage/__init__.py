from covreports.storage.minio import MinioStorageService
from covreports.storage.gcp import GCPStorageService
from covreports.storage.aws import AWSStorageService
from covreports.config import get_config


def get_appropriate_storage_service():
    chosen_storage = get_config('services', 'chosen_storage', default='minio')
    return _get_appropriate_storage_service_given_storage(chosen_storage)


def _get_appropriate_storage_service_given_storage(chosen_storage):
    if chosen_storage == 'gcp':
        gcp_config = get_config('services', 'gcp', default={})
        return GCPStorageService(gcp_config)
    elif chosen_storage == 'aws':
        aws_config = get_config('services', 'aws', default={})
        return AWSStorageService(aws_config)
    else:
        minio_config = get_config('services', 'minio', default={})
        return MinioStorageService(minio_config)
