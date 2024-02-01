import gzip
import logging
from io import BytesIO

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
        bucket = self.storage_client.get_bucket(bucket_name)
        return storage.Blob(path, bucket)

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
        bucket_name,
        path,
        data,
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
            data (str): The data to be written to the file
            reduced_redundancy (bool): Whether a reduced redundancy mode should be used (default: {False})
            is_already_gzipped (bool): Whether the file is already gzipped (default: {False})

        Raises:
            NotImplementedError: If the current instance did not implement this method
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

    def append_to_file(self, bucket_name, path, data):
        """
            Appends more content to the file `path`
            (What happens if the file doesn't exist?)

            Note that this method assumes some non-bytes and instead decodable structure
                at the file

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The desired path of the file
            data (str): The data to be appended to the file

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        try:
            file_contents = "\n".join(
                (self.read_file(bucket_name, path).decode(), data)
            )
        except FileNotInStorageError:
            file_contents = data
        return self.write_file(bucket_name, path, file_contents)

    def read_file(self, bucket_name, path, file_obj=None, *, retry=0):
        """Reads the content of a file

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file

        Raises:
            NotImplementedError: If the current instance did not implement this method
            FileNotInStorageError: If the file does not exist

        Returns:
            bytes : The contents of that file, still encoded as bytes
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
        except google.cloud.exceptions.NotFound:
            raise FileNotInStorageError(f"File {path} does not exist in {bucket_name}")
        except google.resumable_media.common.DataCorruption:
            if retry == 0:
                log.info("Download checksum failed. Trying again")
                return self.read_file(bucket_name, path, file_obj, retry=1)
            raise

    def delete_file(self, bucket_name, path):
        """Deletes a single file from the storage (what happens if the file doesnt exist?)

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file to be deleted

        Raises:
            NotImplementedError: If the current instance did not implement this method
            FileNotInStorageError: If the file does not exist

        Returns:
            bool: True if the deletion was succesful
        """
        blob = self.get_blob(bucket_name, path)
        try:
            blob.delete()
        except google.cloud.exceptions.NotFound:
            raise FileNotInStorageError(f"File {path} does not exist in {bucket_name}")
        return True

    def delete_files(self, bucket_name, paths=[]):
        """Batch deletes a list of files from a given bucket
            (what happens to the files that don't exist?)

        Args:
            bucket_name (str): The name of the bucket for the file lives
            paths (list): A list of the paths to be deletes (default: {[]})

        Raises:
            NotImplementedError: If the current instance did not implement this method

        Returns:
            list: A list of booleans, where each result indicates whether that file was deleted
                successfully
        """
        bucket = self.storage_client.get_bucket(bucket_name)
        blobs = [self.get_blob(bucket_name, path) for path in paths]
        blobs_errored = set()
        bucket.delete_blobs(blobs, on_error=blobs_errored.add)
        return [b not in blobs_errored for b in blobs]

    def list_folder_contents(self, bucket_name, prefix=None, recursive=True):
        """List the contents of a specific folder

        Attention: google ignores the `recursive` param

        Args:
            bucket_name (str): The name of the bucket for the file lives
            prefix: The prefix of the files to be listed (default: {None})
            recursive: Whether the listing should be recursive (default: {True})

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        assert recursive
        bucket = self.storage_client.get_bucket(bucket_name)
        return (self._blob_to_dict(b) for b in bucket.list_blobs(prefix=prefix))

    def _blob_to_dict(self, blob):
        return {"name": blob.name, "size": blob.size}
