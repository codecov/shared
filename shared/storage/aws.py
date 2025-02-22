import gzip
import logging

import boto3
from botocore.exceptions import ClientError

from shared.storage.base import CHUNK_SIZE, BaseStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

log = logging.getLogger(__name__)


class AWSStorageService(BaseStorageService):
    def __init__(self, aws_config):
        self.config = aws_config
        self.storage_client = boto3.client(
            aws_config.get("resource"),
            aws_access_key_id=aws_config.get("aws_access_key_id"),
            aws_secret_access_key=aws_config.get("aws_secret_access_key"),
            region_name=aws_config.get("region_name"),
        )

    def create_root_storage(self, bucket_name="archive", region="us-east-1"):
        """
            Creates root storage (or bucket, as in some terminologies)

        Note:
            AWS API wont return an error if you attempt to create a bucket that
            already exists in us-east-1 region. However, it does return an error
            if you attempt to create a bucket that already exists in any other region.

        Args:
            bucket_name (str): The name of the bucket to be created (default: {'archive'})
            region (str): The region in which the bucket will be created (default: {'us-east-1'})

        Raises:
            BucketAlreadyExistsError: If the bucket already exists
        """

        if region == "us-east-1":
            try:
                self.storage_client.head_bucket(Bucket=bucket_name)
                raise BucketAlreadyExistsError(f"Bucket {bucket_name} already exists")
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    self.storage_client.create_bucket(Bucket=bucket_name)
        else:
            try:
                location = {"LocationConstraint": region}
                self.storage_client.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration=location
                )
            except ClientError as e:
                if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                    raise BucketAlreadyExistsError(
                        f"Bucket {bucket_name} already exists"
                    )
                else:
                    raise
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

        """
        storage_class = "REDUCED_REDUNDANCY" if reduced_redundancy else "STANDARD"
        self.storage_client.put_object(
            Bucket=bucket_name, Key=path, Body=data, StorageClass=storage_class
        )
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
            obj = self.storage_client.get_object(Bucket=bucket_name, Key=path)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotInStorageError(
                    f"File {path} does not exist in {bucket_name}"
                )
            else:
                raise
        content = obj["Body"].read()
        try:
            content = gzip.decompress(content)
        except OSError:
            pass
        if file_obj is None:
            return content
        else:
            chunks = [
                content[i : i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)
            ]
            for chunk in chunks:
                file_obj.write(chunk)

    def delete_file(self, bucket_name, path):
        """Deletes a single file from the storage

        Note:
            AWS returns a 204 regardless if the file is not already
            there in the first place.
            FileNotInStorageError wont be raised if a file doesnt exists.

        Args:
            bucket_name (str): The name of the bucket for the file lives
            path (str): The path of the file to be deleted

        Raises:
            FileNotInStorageError: If the file does not exist

        Returns:
            bool: True if the deletion was succesful
        """
        try:
            self.storage_client.delete_object(Bucket=bucket_name, Key=path)
            return True
        except ClientError:
            raise
