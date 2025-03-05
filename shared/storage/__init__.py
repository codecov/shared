from typing import Literal, cast

from shared.config import get_config
from shared.rollouts.features import NEW_MINIO
from shared.storage.base import BaseStorageService
from shared.storage.minio import MinioStorageService


def get_appropriate_storage_service(
    repoid: int | None = None,
) -> MinioStorageService:
    minio_config = get_config("services", "minio", default={})
    if repoid:
        new_minio_mode = cast(
            Literal["read", "write"] | None,
            NEW_MINIO.check_value(repoid, default=None),  # type: ignore
        )
        return MinioStorageService(
            minio_config,
            new_mode=new_minio_mode,
        )
    else:
        return MinioStorageService(minio_config)
