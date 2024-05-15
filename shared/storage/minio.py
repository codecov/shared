import gzip
import json
import logging
import os
import shutil
import sys
import tempfile
from io import BytesIO

from minio import Minio
from minio.credentials import (
    ChainedProvider,
    EnvAWSProvider,
    EnvMinioProvider,
    IamAwsProvider,
)
from minio.deleteobjects import DeleteObject
from minio.error import MinioException, S3Error

from shared.storage.base import CHUNK_SIZE, BaseStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError

log = logging.getLogger(__name__)


# Service class for interfacing with codecov's underlying storage layer, minio
class MinioStorageService(BaseStorageService):
    def __init__(self, minio_config):
        self.minio_config = minio_config
        log.debug("Connecting to minio with config %s", self.minio_config)

        self.minio_client = self.init_minio_client(
            self.minio_config["host"],
            self.minio_config.get("port"),
            self.minio_config["access_key_id"],
            self.minio_config["secret_access_key"],
            self.minio_config["verify_ssl"],
            self.minio_config.get("iam_auth", False),
            self.minio_config["iam_endpoint"],
            self.minio_config.get("region"),
        )
        log.debug("Done setting up minio client")

    def client(self):
        return self.minio_client if self.minio_client else None

    def init_minio_client(
        self,
        host: str,
        port: str,
        access_key: str = None,
        secret_key: str = None,
        verify_ssl: bool = False,
        iam_auth: bool = False,
        iam_endpoint: str = None,
        region: str = None,
    ):
        """
            Initialize the minio client

        `iam_auth` adds support for IAM base authentication in a fallback pattern.
            The following will be checked in order:

        * EC2 metadata -- a custom endpoint can be provided, default is None.
        * AWS env vars, specifically AWS_ACCESS_KEY and AWS_SECRECT_KEY
        * Minio env vars, specifically MINIO_ACCESS_KEY and MINIO_SECRET_KEY

        to support backward compatibility, the iam_auth setting should be used in the installation
            configuration

        Args:
            host (str): The address of the host where minio lives
            port (str): The port number (as str or int should be ok)
            access_key (str, optional): The access key (optional if IAM is being used)
            secret_key (str, optional): The secret key (optional if IAM is being used)
            verify_ssl (bool, optional): Whether minio should verify ssl
            iam_auth (bool, optional): Whether to use iam_auth
            iam_endpoint (str, optional): The endpoint to try to fetch EC2 metadata
            region (str, optional): The region of the host where minio lives
        """
        if port is not None:
            host = "{}:{}".format(host, port)

        if iam_auth:
            return Minio(
                host,
                secure=verify_ssl,
                region=region,
                credentials=ChainedProvider(
                    providers=[
                        IamAwsProvider(custom_endpoint=iam_endpoint),
                        EnvMinioProvider(),
                        EnvAWSProvider(),
                    ]
                ),
            )
        return Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            secure=verify_ssl,
            region=region,
        )

    # writes the initial storage bucket to storage via minio.
    def create_root_storage(self, bucket_name="archive", region="us-east-1"):
        read_only_policy = {
            "Statement": [
                {
                    "Action": ["s3:GetObject"],
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                }
            ],
            "Version": "2012-10-17",
        }
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                log.debug(
                    "Making bucket on bucket %s on location %s", bucket_name, region
                )
                self.minio_client.make_bucket(bucket_name, location=region)
                log.debug("Setting policy")
                self.minio_client.set_bucket_policy(
                    bucket_name, json.dumps(read_only_policy)
                )
                log.debug("Done creating root storage")
                return {"name": bucket_name}
            else:
                raise BucketAlreadyExistsError(f"Bucket {bucket_name} already exists")
        # todo should only pass or raise
        except S3Error as e:
            if e.code == "BucketAlreadyOwnedByYou":
                raise BucketAlreadyExistsError(f"Bucket {bucket_name} already exists")
            elif e.code == "BucketAlreadyExists":
                pass
            raise
        except MinioException:
            raise

    # Writes a file to storage will gzip if not compressed already
    def write_file(
        self,
        bucket_name,
        path,
        data,
        reduced_redundancy=False,
        *,
        is_already_gzipped: bool = False,
    ):
        if isinstance(data, str):
            data = data.encode()

        if isinstance(data, bytes):
            if not is_already_gzipped:
                out = BytesIO()
                with gzip.GzipFile(fileobj=out, mode="w", compresslevel=9) as gz:
                    gz.write(data)
            else:
                out = BytesIO(data)

            # get file size
            out.seek(0, os.SEEK_END)
            out_size = out.tell()
        else:
            # data is already a file-like object
            if not is_already_gzipped:
                _, filename = tempfile.mkstemp()
                with gzip.open(filename, "wb") as f:
                    shutil.copyfileobj(data, f)
                out = open(filename, "rb")
            else:
                out = data

            out_size = os.stat(filename).st_size

        try:
            # reset pos for minio reading.
            out.seek(0)

            headers = {"Content-Encoding": "gzip"}
            if reduced_redundancy:
                headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"
            self.minio_client.put_object(
                bucket_name,
                path,
                out,
                out_size,
                metadata=headers,
                content_type="text/plain",
            )
            return True

        except MinioException:
            raise

    """
        Retrieves object from path, appends data, writes back to path.
    """

    def append_to_file(self, bucket_name, path, data):
        try:
            file_contents = "\n".join(
                (self.read_file(bucket_name, path).decode(), data)
            )
        except FileNotInStorageError:
            file_contents = data
        except MinioException:
            raise
        return self.write_file(bucket_name, path, file_contents)

    def read_file(self, bucket_name, path, file_obj=None):
        try:
            res = self.minio_client.get_object(bucket_name, path)
            if file_obj is None:
                data = BytesIO()
                for d in res.stream(CHUNK_SIZE):
                    data.write(d)
                data.seek(0)
                return data.getvalue()
            else:
                for d in res.stream(CHUNK_SIZE):
                    file_obj.write(d)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotInStorageError(
                    f"File {path} does not exist in {bucket_name}"
                )
            raise e
        except MinioException as e:
            raise

    """
        Deletes file url in specified bucket.
        Return true on successful
        deletion, returns a ResponseError otherwise.
    """

    def delete_file(self, bucket_name, url):
        try:
            # delete a file given a bucket name and a url
            self.minio_client.remove_object(bucket_name, url)
            return True
        except MinioException:
            raise

    def delete_files(self, bucket_name, urls=[]):
        try:
            for del_err in self.minio_client.remove_objects(
                bucket_name, [DeleteObject(url) for url in urls]
            ):
                print("Deletion error: {}".format(del_err))
            return [True] * len(urls)
        except MinioException:
            raise

    def list_folder_contents(self, bucket_name, prefix=None, recursive=True):
        return (
            self.object_to_dict(b)
            for b in self.minio_client.list_objects(bucket_name, prefix, recursive)
        )

    def object_to_dict(self, obj):
        return {"name": obj.object_name, "size": obj.size}

    # TODO remove this function -- just using it for output during testing.
    def write(self, string, silence=False):
        if not silence:
            sys.stdout.write((string or "") + "\n")
