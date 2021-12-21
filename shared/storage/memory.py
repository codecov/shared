from collections import defaultdict

from shared.storage.base import BaseStorageService
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
        self, bucket_name, path, data, reduced_redundancy=False, gzipped=False
    ):
        """
            Writes a new file with the contents of `data`
            (What happens if the file already exists?)


        Args:
            bucket_name (str): The name of the bucket for the file to be created on
            path (str): The desired path of the file
            data (str): The data to be written to the file
            reduced_redundancy (bool): Whether a reduced redundancy mode should be used (default: {False})
            gzipped (bool): Whether the file should be gzipped on write (default: {False})

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        if isinstance(data, str):
            data = data.encode()
        self.storage[bucket_name][path] = data
        return True

    def append_to_file(self, bucket_name, path, data):
        """
            Appends more content to the file `path`
            (What happens if the file doesn't exist?)

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The desired path of the file
            data (str): The data to be appended to the file

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        if isinstance(data, str):
            data = data.encode()
        if path not in self.storage[bucket_name]:
            return self.write_file(bucket_name, path, data)
        else:
            new_content = b"\n".join([self.storage[bucket_name].get(path, b""), data])
            return self.write_file(bucket_name, path, new_content)

    def read_file(self, bucket_name, path):
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
            return self.storage[bucket_name][path]
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
        results = []
        for path in paths:
            try:
                results.append(self.delete_file(bucket_name, path))
            except FileNotInStorageError:
                results.append(False)
        return results

    def list_folder_contents(self, bucket_name, prefix=None, recursive=True):
        """List the contents of a specific folder

        Args:
            bucket_name (str): The name of the bucket for the file lives
            prefix: The prefix of the files to be listed (default: {None})
            recursive: Whether the listing should be recursive (default: {True})

        Raises:
            NotImplementedError: If the current instance did not implement this method
        """
        res = []
        for key in self.storage[bucket_name]:
            if prefix is None or key.startswith(prefix):
                res.append(
                    {"name": key, "size": len(self.storage[bucket_name][key].decode())}
                )
        return res
