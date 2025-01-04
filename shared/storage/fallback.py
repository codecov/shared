import logging

from shared.storage.base import BaseStorageService
from shared.storage.exceptions import FileNotInStorageError

log = logging.getLogger(__name__)


class StorageWithFallbackService(BaseStorageService):
    def __init__(self, main_service, fallback_service):
        self.main_service = main_service
        self.fallback_service = fallback_service

    def create_root_storage(self, bucket_name="archive", region="us-east-1"):
        res = self.main_service.create_root_storage(bucket_name, region)
        self.fallback_service.create_root_storage(bucket_name, region)
        return res

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

        Args:
            bucket_name (str): The name of the bucket for the file to be created on
            path (str): The desired path of the file
            data (str): The data to be written to the file
            reduced_redundancy (bool): Whether a reduced redundancy mode should be used (default: {False})
            is_already_gzipped (bool): Whether the file is already gzipped (default: {False})

        """
        return self.main_service.write_file(
            bucket_name,
            path,
            data,
            reduced_redundancy,
            is_already_gzipped=is_already_gzipped,
        )

    def read_file(self, bucket_name, path, file_obj=None):
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
        try:
            return self.main_service.read_file(bucket_name, path, file_obj=file_obj)
        except FileNotInStorageError:
            log.info("File not in first storage, looking into second one")
            return self.fallback_service.read_file(bucket_name, path, file_obj=file_obj)

    def delete_file(self, bucket_name, path):
        """Deletes a single file from the storage

        Note: Not all implementations raise a FileNotInStorageError
            if the file is not already there in the first place.
            It seems that minio, for example, returns a 204 regardless.
            So while you should prepare for a FileNotInStorageError,
            know that if it is not raise, it doesn't mean the file
            was there beforehand.

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file to be deleted

        Raises:
            NotImplementedError: If the current instance did not implement this method
            FileNotInStorageError: If the file does not exist

        Returns:
            bool: True if the deletion was succesful
        """
        first_deletion = self.main_service.delete_file(bucket_name, path)
        second_deletion = self.fallback_service.delete_file(bucket_name, path)
        return first_deletion and second_deletion

    def delete_files(self, bucket_name: str, paths: list[str]) -> list[bool]:
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
        first_results = self.main_service.delete_files(bucket_name, paths)
        second_results = self.fallback_service.delete_files(bucket_name, paths)
        return [f and s for f, s in zip(first_results, second_results)]

    def list_folder_contents(self, bucket_name, prefix=None, recursive=True):
        """List the contents of a specific folder

        Args:
            bucket_name (str): The name of the bucket for the file lives
            prefix: The prefix of the files to be listed (default: {None})
            recursive: Whether the listing should be recursive (default: {True})

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        return self.main_service.list_folder_contents(bucket_name, prefix, recursive)
