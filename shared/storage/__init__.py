from typing import Literal, cast

from shared.config import get_config
from shared.rollouts.features import NEW_MINIO
from shared.storage.base import BaseStorageService
from shared.storage.minio import MinioStorageService


def get_appropriate_storage_service(
    repoid: int | None = None,
    force_minio=False,
) -> BaseStorageService:
    return get_minio_storage_service(repoid)


def get_minio_storage_service(
    repo_id: int | None,
) -> MinioStorageService:
    minio_config = get_config("services", "minio", default={})
    if repo_id:
        new_minio_mode = cast(
            Literal["read", "write"] | None,
            NEW_MINIO.check_value(repo_id, default=None),  # type: ignore
        )
        return MinioStorageService(
            minio_config,
            new_mode=new_minio_mode,
        )
    else:
        return MinioStorageService(minio_config)
