import gzip
import io
import json
import os
import tempfile
from uuid import uuid4

import pytest

from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.gcp import GCPStorageService

# The GCS credentials (a service account JSON)
# used to run these tests can be provided in the following way:
#
# - as serialized JSON, using the `GOOGLE_APPLICATION_CREDENTIALS_JSON` env variable
# - as a file path, using the `GOOGLE_APPLICATION_CREDENTIALS` env variable
# - using a `gcs-service-account.json` in the root of the repository
#
# Sentry employees can find this file under the `symbolicator-gcs-test-key` entry in 1Password.
#
# This test methodology is copied from:
# <https://github.com/getsentry/symbolicator/blob/2ef1a089cbf6fa9a30a14f82d89814b431e95717/crates/symbolicator-test/src/lib.rs#L479-L553>


def try_loading_credentials():
    try:
        if credentials := os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
            return json.loads(credentials)
        credentials_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_file:
            import pathlib

            credentials_file = (
                pathlib.Path(__file__)
                .parent # storage
                .parent # unit
                .parent # tests
                / "gcs-service-account.json"
            ).resolve()  # fmt: skip
        print(credentials_file)
        with open(credentials_file, "rb") as f:
            return json.loads(f.read())
    except Exception:
        return None


IS_CI = os.environ.get("CI", "false") == "true"
CREDENTIALS = try_loading_credentials()

pytestmark = pytest.mark.skipif(
    not IS_CI and not CREDENTIALS,
    reason="GCS credentials not available for local testing",
)

# The service account being used has the following bucket configured:
BUCKET_NAME = "sentryio-symbolicator-cache-test"


def make_storage() -> GCPStorageService:
    assert CREDENTIALS, "expected GCS credentials to be properly configured"
    return GCPStorageService(CREDENTIALS)


def ensure_bucket(storage: GCPStorageService):
    pass


@pytest.mark.skip(reason="we currently have no way of cleaning up upstream buckets")
def test_create_bucket():
    storage = make_storage()
    bucket_name = uuid4().hex

    res = storage.create_root_storage(bucket_name, region="")
    assert res == {"name": bucket_name}


@pytest.mark.skip(reason="we currently have no way of cleaning up upstream buckets")
def test_create_bucket_already_exists():
    storage = make_storage()
    bucket_name = uuid4().hex

    storage.create_root_storage(bucket_name)
    with pytest.raises(BucketAlreadyExistsError):
        storage.create_root_storage(bucket_name)


def test_write_then_read_file():
    storage = make_storage()
    path = f"test_write_then_read_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file á"

    ensure_bucket(storage)
    writing_result = storage.write_file(BUCKET_NAME, path, data)
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


def test_write_then_read_file_obj():
    storage = make_storage()
    path = f"test_write_then_read_file_obj/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file_obj á"

    ensure_bucket(storage)

    _, local_path = tempfile.mkstemp()
    with open(local_path, "w") as f:
        f.write(data)
    with open(local_path, "rb") as f:
        writing_result = storage.write_file(BUCKET_NAME, path, f)
    assert writing_result

    _, local_path = tempfile.mkstemp()
    with open(local_path, "wb") as f:
        storage.read_file(BUCKET_NAME, path, file_obj=f)
    with open(local_path, "rb") as f:
        assert f.read().decode() == data


def test_manually_then_read_then_write_then_read_file():
    storage = make_storage()
    path = f"test_manually_then_read_then_write_then_read_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_manually_then_read_then_write_then_read_file á"

    ensure_bucket(storage)

    blob = storage.get_blob(BUCKET_NAME, path)
    blob.upload_from_string("some data around")
    assert storage.read_file(BUCKET_NAME, path).decode() == "some data around"
    blob.reload()
    assert blob.content_type == "text/plain"
    assert blob.content_encoding is None

    data = "lorem ipsum dolor test_write_then_read_file á"
    assert storage.write_file(BUCKET_NAME, path, data)
    assert storage.read_file(BUCKET_NAME, path).decode() == data
    blob = storage.get_blob(BUCKET_NAME, path)
    blob.reload()
    assert blob.content_type == "text/plain"
    assert blob.content_encoding == "gzip"


def test_write_then_read_file_gzipped():
    storage = make_storage()
    path = f"test_write_then_read_file_gzipped/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_read_file_gzipped á"

    writing_result = storage.write_file(
        BUCKET_NAME, path, gzip.compress(data.encode()), is_already_gzipped=True
    )
    assert writing_result
    reading_result = storage.read_file(BUCKET_NAME, path)
    assert reading_result.decode() == data


def test_read_file_does_not_exist():
    storage = make_storage()
    path = f"test_read_file_does_not_exist/{uuid4().hex}"

    ensure_bucket(storage)
    with pytest.raises(FileNotInStorageError):
        storage.read_file(BUCKET_NAME, path)


def test_read_file_application_gzip():
    storage = make_storage()
    path = f"test_read_file_application_gzip/{uuid4().hex}"
    content_to_upload = "content to write\nThis is crazy\nWhy does this work"

    blob = storage.get_blob(BUCKET_NAME, path)
    with io.BytesIO() as f:
        with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9) as fgz:
            fgz.write(content_to_upload.encode())
        blob.content_encoding = "gzip"
        blob.upload_from_file(
            f,
            size=f.tell(),
            rewind=True,
            content_type="application/x-gzip",
        )

    content = storage.read_file(BUCKET_NAME, path)
    assert content.decode() == content_to_upload


def test_write_then_delete_file():
    storage = make_storage()
    path = f"test_write_then_delete_file/{uuid4().hex}"
    data = "lorem ipsum dolor test_write_then_delete_file á"

    ensure_bucket(storage)
    writing_result = storage.write_file(BUCKET_NAME, path, data)
    assert writing_result

    deletion_result = storage.delete_file(BUCKET_NAME, path)
    assert deletion_result is True
    with pytest.raises(FileNotInStorageError):
        storage.read_file(BUCKET_NAME, path)


def test_delete_file_doesnt_exist():
    storage = make_storage()
    path = f"test_delete_file_doesnt_exist/{uuid4().hex}"

    ensure_bucket(storage)
    with pytest.raises(FileNotInStorageError):
        storage.delete_file(BUCKET_NAME, path)


def test_batch_delete_files():
    storage = make_storage()
    path = f"test_batch_delete_files/{uuid4().hex}"
    path_1 = f"{path}/result_1.txt"
    path_2 = f"{path}/result_2.txt"
    path_3 = f"{path}/result_3.txt"
    paths = [path_1, path_2, path_3]
    data = "lorem ipsum dolor test_batch_delete_files á"

    ensure_bucket(storage)
    storage.write_file(BUCKET_NAME, path_1, data)
    storage.write_file(BUCKET_NAME, path_3, data)

    deletion_result = storage.delete_files(BUCKET_NAME, paths)
    assert deletion_result == [True, False, True]
    for p in paths:
        with pytest.raises(FileNotInStorageError):
            storage.read_file(BUCKET_NAME, p)


@pytest.mark.skip(
    reason="the service account used for testing does not have bucket list permissions"
)
def test_list_folder_contents():
    storage = make_storage()
    path = f"test_list_folder_contents/{uuid4().hex}"
    path_1 = "/result_1.txt"
    path_2 = "/result_2.txt"
    path_3 = "/result_3.txt"
    path_4 = "/x1/result_1.txt"
    path_5 = "/x1/result_2.txt"
    path_6 = "/x1/result_3.txt"
    all_paths = [path_1, path_2, path_3, path_4, path_5, path_6]

    ensure_bucket(storage)
    for i, p in enumerate(all_paths):
        data = f"Lorem ipsum on file {p} for {i * 'po'}"
        storage.write_file(BUCKET_NAME, f"{path}{p}", data)

    results_1 = sorted(
        storage.list_folder_contents(BUCKET_NAME, path),
        key=lambda x: x["name"],
    )
    assert results_1 == [
        {"name": f"{path}{path_1}", "size": 38},
        {"name": f"{path}{path_2}", "size": 40},
        {"name": f"{path}{path_3}", "size": 42},
        {"name": f"{path}{path_4}", "size": 47},
        {"name": f"{path}{path_5}", "size": 49},
        {"name": f"{path}{path_6}", "size": 51},
    ]

    results_2 = sorted(
        storage.list_folder_contents(BUCKET_NAME, f"{path}/x1"),
        key=lambda x: x["name"],
    )
    assert results_2 == [
        {"name": f"{path}{path_4}", "size": 47},
        {"name": f"{path}{path_5}", "size": 49},
        {"name": f"{path}{path_6}", "size": 51},
    ]
