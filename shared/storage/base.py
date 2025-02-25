from abc import ABC, abstractmethod
from typing import BinaryIO, overload

CHUNK_SIZE = 1024 * 32
PART_SIZE = 1024 * 1024 * 20  # 20MiB


# Interface class for interfacing with codecov's underlying storage layer
class BaseStorageService(ABC):
    @abstractmethod
    def create_root_storage(self, bucket_name="archive", region="us-east-1"):
        """
            Creates root storage (or bucket, as in some terminologies)

        Args:
            bucket_name (str): The name of the bucket to be created (default: {'archive'})
            region (str): The region in which the bucket will be created (default: {'us-east-1'})

        Raises:
            NotImplementedError: If the current instance did not implement this method
            BucketAlreadyExistsError: If the bucket already exists
        """
        raise NotImplementedError()

    @abstractmethod
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
        raise NotImplementedError()

    @abstractmethod
    @overload
    def read_file(self, bucket_name: str, path: str) -> bytes: ...

    @abstractmethod
    @overload
    def read_file(self, bucket_name: str, path: str, file_obj: BinaryIO) -> None: ...

    @abstractmethod
    def read_file(
        self, bucket_name: str, path: str, file_obj: BinaryIO | None = None
    ) -> bytes | None:
        """Reads the content of a file

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file
            file_obj (file like): A file-like object in which to write the contents

        Raises:
            NotImplementedError: If the current instance did not implement this method
            FileNotInStorageError: If the file does not exist

        Returns:
            bytes : The contents of that file, still encoded as bytes (only when file_obj is None)
        """
        raise NotImplementedError()

    @abstractmethod
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
        raise NotImplementedError()


class PresignedURLService(ABC):
    @abstractmethod
    def create_presigned_put(self, bucket: str, path: str, expires: int) -> str: ...

    @abstractmethod
    def create_presigned_get(self, bucket: str, path: str, expires: int) -> str: ...
