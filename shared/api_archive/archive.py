import json
import logging
from base64 import b16encode
from enum import Enum
from hashlib import md5

import sentry_sdk

import shared.storage
from shared.config import get_config
from shared.utils.ReportEncoder import ReportEncoder

log = logging.getLogger(__name__)


# TODO deduplicate this logic from worker and shared
class MinioEndpoints(Enum):
    chunks = "{version}/repos/{repo_hash}/commits/{commitid}/chunks.txt"
    json_data = "{version}/repos/{repo_hash}/commits/{commitid}/json_data/{table}/{field}/{external_id}.json"
    json_data_no_commit = (
        "{version}/repos/{repo_hash}/json_data/{table}/{field}/{external_id}.json"
    )
    raw = "v4/raw/{date}/{repo_hash}/{commit_sha}/{reportid}.txt"
    raw_with_upload_id = (
        "v4/raw/{date}/{repo_hash}/{commit_sha}/{reportid}/{uploadid}.txt"
    )
    profiling_upload = (
        "{version}/repos/{repo_hash}/profilinguploads/{profiling_version}/{location}"
    )
    static_analysis_single_file = (
        "{version}/repos/{repo_hash}/static_analysis/files/{location}"
    )
    test_results = "test_results/v1/raw/{date}/{repo_hash}/{commit_sha}/{uploadid}.txt"

    def get_path(self, **kwaargs):
        return self.value.format(**kwaargs)


class ArchiveService(object):
    """
    Service class for performing archive operations.
    Meant to work against the underlying `StorageService`.
    """

    root: str
    """
    The root level of the archive.
    In s3 terms, this would be the name of the bucket
    """

    storage_hash: str | None
    """
    A hash key of the repo for internal storage
    """

    ttl = 10
    """
    Time to life, how long presigned PUTs/GETs should live
    """

    def __init__(self, repository, ttl=None):
        self.root = get_config("services", "minio", "bucket", default="archive")
        # Set TTL from config and default to existing value
        self.ttl = ttl or int(get_config("services", "minio", "ttl", default=self.ttl))

        # The `api_archive.ArchiveService` is always using `minio`
        self.storage = shared.storage.get_appropriate_storage_service(
            repository.repoid if repository else None
        )

        self.storage_hash = self.get_archive_hash(repository) if repository else None

    @classmethod
    def get_archive_hash(cls, repository) -> str:
        """
        Generates a hash key from repo specific information.
        Provides slight obfuscation of data in minio storage
        """
        _hash = md5()
        hash_key = get_config("services", "minio", "hash_key", default="")
        val = "".join(
            map(
                str,
                (
                    repository.repoid,
                    repository.service,
                    repository.service_id,
                    hash_key,
                ),
            )
        ).encode()
        _hash.update(val)
        return b16encode(_hash.digest()).decode()

    def write_json_data_to_storage(
        self,
        commit_id,
        table: str,
        field: str,
        external_id: str,
        data: dict,
        *,
        encoder=ReportEncoder,
    ):
        if not self.storage_hash:
            raise ValueError("No hash key provided")
        if commit_id is None:
            # Some classes don't have a commit associated with them
            # For example Pull belongs to multiple commits.
            path = MinioEndpoints.json_data_no_commit.get_path(
                version="v4",
                repo_hash=self.storage_hash,
                table=table,
                field=field,
                external_id=external_id,
            )
        else:
            path = MinioEndpoints.json_data.get_path(
                version="v4",
                repo_hash=self.storage_hash,
                commitid=commit_id,
                table=table,
                field=field,
                external_id=external_id,
            )
        stringified_data = json.dumps(data, cls=encoder)
        self.write_file(path, stringified_data)
        return path

    @sentry_sdk.trace
    def write_file(
        self, path, data, reduced_redundancy=False, is_already_gzipped=False
    ):
        """
        Writes a generic file to the archive -- it's typically recommended to
        not use this in lieu of the convenience methods write_raw_upload and
        write_chunks
        """
        self.storage.write_file(
            self.root,
            path,
            data,
            reduced_redundancy=reduced_redundancy,
            is_already_gzipped=is_already_gzipped,
        )

    @sentry_sdk.trace
    def read_file(self, path: str) -> str:
        """
        Generic method to read a file from the archive
        """
        contents = self.storage.read_file(self.root, path)
        return contents.decode()

    @sentry_sdk.trace
    def delete_file(self, path: str) -> None:
        """
        Generic method to delete a file from the archive.
        """
        self.storage.delete_file(self.root, path)

    def read_chunks(self, commit_sha: str) -> str:
        """
        Convenience method to read a chunks file from the archive.
        """
        if not self.storage_hash:
            raise ValueError("No hash key provided")
        path = MinioEndpoints.chunks.get_path(
            version="v4", repo_hash=self.storage_hash, commitid=commit_sha
        )
        return self.read_file(path)

    def create_presigned_put(self, path: str) -> str:
        return self.storage.create_presigned_put(self.root, path, self.ttl)
