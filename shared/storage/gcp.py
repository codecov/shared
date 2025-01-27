import gzip
import logging
from typing import IO

import google.cloud.exceptions
from google.cloud import storage
from google.oauth2.service_account import Credentials

from shared.storage.base import BaseStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

log = logging.getLogger(__name__)


class GCPStorageService(BaseStorageService):
    def __init__(self, gcp_config):
        self.config = gcp_config
        self.credentials = self.load_credentials(gcp_config)
        self.storage_client = storage.Client(
            project=self.credentials.project_id, credentials=self.credentials
        )

    def load_credentials(self, gcp_config):
        location = gcp_config.get("google_credentials_location")
        if location:
            return Credentials.from_service_account_file(filename=location)
        return Credentials.from_service_account_info(gcp_config)

    def get_blob(self, bucket_name, path):
        bucket = self.storage_client.bucket(bucket_name)
        return bucket.blob(path)

    def create_root_storage(self, bucket_name="archive", region="us-east-1"):
        """
            Creates root storage (or bucket_name, as in some terminologies)

        Args:
            bucket_name (str): The name of the bucket to be created (default: {'archive'})
            region (str): The region in which the bucket will be created (default: {'us-east-1'})

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        try:
            bucket = self.storage_client.create_bucket(bucket_name)
            return {"name": bucket.name}
        except google.cloud.exceptions.Conflict:
            raise BucketAlreadyExistsError(f"Bucket {bucket_name} already exists")

    def write_file(
        self,
        bucket_name: str,
        path: str,
        data: str | bytes | IO,
        reduced_redundancy=False,
        *,
        is_already_gzipped: bool = False,
    ):
        """
        Writes a new file with the contents of `data`
        (What happens if the file already exists?)


        Args:
            bucket_name (str): The name of the bucket for the file to be created on
            path (str): The desired path of the file
            data: The data to be written to the file
            reduced_redundancy (bool): Whether a reduced redundancy mode should be used (default: {False})
            is_already_gzipped (bool): Whether the file is already gzipped (default: {False})
        """
        blob = self.get_blob(bucket_name, path)

        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, bytes):
            if not is_already_gzipped:
                data = gzip.compress(data)
            blob.content_encoding = "gzip"
            blob.upload_from_string(data)
            return True
        else:
            # data is a file-like object
            blob.upload_from_file(data)
            return True

    def read_file(
        self, bucket_name: str, path: str, file_obj: IO | None = None, retry=0
    ) -> bytes:
        """Reads the content of a file

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file

        Raises:
            FileNotInStorageError: If the file does not exist

        Returns:
            bytes: The contents of that file, still encoded as bytes
        """
        blob = self.get_blob(bucket_name, path)

        try:
            blob.reload()
            if (
                blob.content_type == "application/x-gzip"
                and blob.content_encoding == "gzip"
            ):
                blob.content_type = "text/plain"
                blob.content_encoding = "gzip"
                blob.patch()

            if file_obj is None:
                return blob.download_as_bytes(checksum="crc32c")
            else:
                blob.download_to_file(file_obj, checksum="crc32c")
                return b""  # NOTE: this is to satisfy the return type
        except google.cloud.exceptions.NotFound:
            raise FileNotInStorageError(f"File {path} does not exist in {bucket_name}")
        except google.resumable_media.common.DataCorruption:
            if retry == 0:
                log.info("Download checksum failed. Trying again")
                return self.read_file(bucket_name, path, file_obj, retry=1)
            raise

    def delete_file(self, bucket_name: str, path: str) -> bool:
        """Deletes a single file from the storage (what happens if the file doesnt exist?)

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file to be deleted

        Raises:
            FileNotInStorageError: If the file does not exist

        Returns:
            bool: True if the deletion was successful
        """
        blob = self.get_blob(bucket_name, path)
        try:
            blob.delete()
        except google.cloud.exceptions.NotFound:
            raise FileNotInStorageError(f"File {path} does not exist in {bucket_name}")
        return True
