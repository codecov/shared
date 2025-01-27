from collections import defaultdict

from shared.storage.base import CHUNK_SIZE, BaseStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError


class MemoryStorageService(BaseStorageService):
    """
        This Service is not meant to serve as a real storage service.
        It provides way to deal with testing and such

    Attributes:
        config (dict): The config for this
    """

    def __init__(self, config):
        self.config = config
        self.root_storage_created = False
        self.storage = defaultdict(dict)

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
        if self.root_storage_created:
            raise BucketAlreadyExistsError()
        self.root_storage_created = True
        return {"name": bucket_name}

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
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, bytes):
            self.storage[bucket_name][path] = data
        else:
            # data is a file-like object
            data.seek(0)
            self.storage[bucket_name][path] = data.read()
        return True

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
            data = self.storage[bucket_name][path]
            if file_obj is None:
                return data
            else:
                chunks = [
                    data[i : i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)
                ]
                for chunk in chunks:
                    file_obj.write(chunk)
        except KeyError:
            raise FileNotInStorageError()

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
        try:
            del self.storage[bucket_name][path]
        except KeyError:
            raise FileNotInStorageError()
        return True
