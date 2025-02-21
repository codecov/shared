import logging
from datetime import timedelta

from shared.config import get_config
from shared.rollouts.features import USE_NEW_MINIO
from shared.storage.minio import MinioStorageService
from shared.storage.new_minio import NewMinioStorageService

log = logging.getLogger(__name__)


MINIO_SERVICE = None


# Service class for interfacing with codecov's underlying storage layer, minio
class StorageService:
    def __init__(self, repoid: int | None = None, in_config=None):
        global MINIO_SERVICE  # noqa: PLW0603

        minio_config: dict

        # init minio
        if in_config is None:
            minio_config = get_config("services", "minio", default={})
        else:
            minio_config = in_config

        if "host" not in minio_config:
            minio_config["host"] = "minio"
        if "port" not in minio_config:
            minio_config["port"] = 9000
        if "iam_auth" not in minio_config:
            minio_config["iam_auth"] = False
        if "iam_endpoint" not in minio_config:
            minio_config["iam_endpoint"] = None

        if not MINIO_SERVICE:
            use_new = repoid and USE_NEW_MINIO.check_value(repoid)
            if use_new:
                MINIO_SERVICE = NewMinioStorageService(minio_config)
            else:
                MINIO_SERVICE = MinioStorageService(minio_config)
            log.info("----- created minio_client: ---- ")
        self.minio_service = MINIO_SERVICE

    def create_presigned_put(self, bucket, path, expires):
        assert MINIO_SERVICE is not None
        expires = timedelta(seconds=expires)
        return MINIO_SERVICE.minio_client.presigned_put_object(bucket, path, expires)

    def create_presigned_get(self, bucket, path, expires):
        assert MINIO_SERVICE is not None
        expires = timedelta(seconds=expires)
        return MINIO_SERVICE.minio_client.presigned_get_object(bucket, path, expires)
