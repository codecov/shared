import pytest

from shared.storage.aws import AWSStorageService
from shared.storage.exceptions import BucketAlreadyExistsError, FileNotInStorageError
from shared.storage.fallback import StorageWithFallbackService
from shared.storage.gcp import GCPStorageService
from tests.base import BaseTestCase

# DONT WORRY, this is generated for the purposes of validation, and is not the real
# one on which the code ran
fake_private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCnND/Neha4aNJ6
YqMFFeYvjO+ZS2v0v2UQJajN02dOsquWq6lldpXi6NlbV9PMEfn7YuycxbWf92vk
kzcqtODW4xq8lC+DjWPbcrTQltzAyedRYX9q7xoF9WrTaW2feNIOk5fnwrZRiL3z
bwK3R53DzK3v6MQbl9XGQgKHppKDPi04XiwtVKhU1Ej8keoaG+iWALKM17UR4a2w
jBMdJYvnMNNJm8Rw+/sNOLWm/5M0v0BBIOVxr5M1VE5JoIMeeB7nwc+sxmxYj7I3
W8Xv7VpLtUNDZ3ir6tQk+G1sPtaHSJBlYmkfK/WOcKxNIB9OmUXVz1E407Sl/EwH
EYFuULF9AgMBAAECggEABPyLbJLYC57grBK1/uhUyZU/7gfwS8fLeUxOOPk1iwTM
Fj2/Ww3K0Y4VMWKwp9Tfai5clR5WWNN1rcbwLb9gNzhlqzsWIau9TyWgG9pr8fnz
gptQQ/2mfof/rBdoVAmz5ghjzt8hNdRIqfJlF9c0bsrzYwTDmHkSQIvmbGo801oi
Z6RbPATA4EhZMNGb6iXptCe/F9rX0+SV2WbBtWTIbi0wtMRNQNqM11MggoVaYGNR
/hsNuJtCN2qTeKtw8P+Kx2Kqxa0BbTy7ltC64h0S1huW/7wEFtT4ttBGO+gh8vkQ
zlrm8xS02rBeJNVSUpjLN5TpL1KrqT9vlY2/UQ6j5wKBgQDr8/U9N2CC8bwEz+94
fSKRbMAlvFx1Dx4JhxprV3i5o7L0oQ/nj8jPcRInF1lCh83iZbwMMKJcERUwST/A
fdsnE07QuLOCUDuTcf4m+iELrQVFyl5dxG6bvxWu3+8+vChVKyU8/ntlmP4Y6cKJ
hs2xkwIFRnr48vOcTT1YGyZyNwKBgQC1aPwKOI76WwKXt7IhfEBqmktSxu2jEOvi
xZ+dZ7K9DNt4XmkmiRODYf/wg7+bkH6UF6N6y/VVs9PcBV3dOWc65qmYBhza8CRV
13bwg/t3ZXV+YULCYb813z1xDMEKUkuMk4o2zgVhV/sUHW1IQEgIyKWCZ1ScA0/U
mRsanYBv6wKBgANYPPS2MT8J8DFdRTa/B1tqYDrotaLPKQzXhm9ZGRQAlwvSsKgG
qMEQCELXmONRi4CXEphVpCeL8nHxx96RqiaepnJc++Zv/rgzWHfy+b7xn+6CVN4d
Z7f7eHI3KGwKPMQgTXHU5ajmB0wRHDnY2FeZDuFGQ33966gejC0QjXX3AoGBAIGP
EfnmvM42M1rReamKiKLZwRPEOLFuA1l41G7hQXjc9t03aBd6bHI3ikdmgHCEuLHh
VAL+KR/lB1iqiIfXWE9rrxGAxBjkyr533F0XlX+G+Wuh4MDceGfsIIBdoHxTm9sw
/9P2PUdxQ0LxZTvllMyZKANC8t1dTCVEl2PhunmzAoGBAM9upD3S7H7cOQq8nDpj
SrSB1MWd+4xuWy0Ik22WF4yWNQLx396g5oZaIBPzQjeiddt9OijaPYpXDDhXehib
nNHY8NwDM/i9kXrl4l5TXg6j7GWBgqYGramhKPior1+Szfw9QNlBUC5E2GZkf3DZ
hUVr40ZOOnf1HpBc2um+6DAj
-----END PRIVATE KEY-----
"""

gcp_config = {
    "type": "service_account",
    "project_id": "genuine-polymer-165712",
    "private_key_id": "e0098875a6be7fd0fb8d5b5efd6b6f662eff7295",
    "private_key": fake_private_key,
    "client_email": "codecov-marketing-deployment@genuine-polymer-165712.iam.gserviceaccount.com",
    "client_id": "109377049763026714378",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/codecov-marketing-deployment%40genuine-polymer-165712.iam.gserviceaccount.com",
}


aws_config = {
    "resource": "s3",
    "aws_access_key_id": "testrobl3cz4i1to1noa",
    "aws_secret_access_key": "vMTpbJX/vMTpbJX",
    "region_name": "us-east-1",
}


@pytest.fixture()
def storage_service():
    gcp_storage = GCPStorageService(gcp_config)
    aws_storage = AWSStorageService(aws_config)
    return StorageWithFallbackService(gcp_storage, aws_storage)


class TestFallbackStorageService(BaseTestCase):
    def test_create_bucket(self, codecov_vcr, storage_service):
        storage = storage_service
        bucket_name = "testingarchive20190210001"
        res = storage.create_root_storage(bucket_name)
        assert res["name"] == "testingarchive20190210001"

    def test_create_bucket_already_exists(self, codecov_vcr, storage_service):
        storage = storage_service
        bucket_name = "testingarchive20190210001"
        with pytest.raises(BucketAlreadyExistsError):
            storage.create_root_storage(bucket_name)

    def test_write_then_read_file(self, codecov_vcr, storage_service):
        storage = storage_service
        path = "test_write_then_read_file/result"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "testingarchive20190210001"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == data

    def test_read_file_does_not_exist(self, request, codecov_vcr, storage_service):
        storage = storage_service
        path = f"{request.node.name}/does_not_exist.txt"
        bucket_name = "testingarchive20190210001"
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_read_file_does_not_exist_on_first_but_exists_on_second(
        self, request, codecov_vcr, storage_service
    ):
        storage = storage_service
        path = f"{request.node.name}/does_not_exist_on_first_but_exists_on_second.txt"
        bucket_name = "testingarchive20190210001"
        storage_service.fallback_service.write_file(
            bucket_name, path, "some_data_over_there"
        )
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == "some_data_over_there"

    def test_read_file_does_exist_on_first_but_not_exists_on_second(
        self, request, codecov_vcr, storage_service
    ):
        storage = storage_service
        path = f"{request.node.name}/does_exist_on_first_but_not_exists_on_second.txt"
        bucket_name = "testingarchive20190210001"
        storage_service.main_service.write_file(
            bucket_name, path, "some_different_data"
        )
        reading_result = storage.read_file(bucket_name, path)
        assert reading_result.decode() == "some_different_data"

    def test_write_then_delete_file(self, request, codecov_vcr, storage_service):
        storage = storage_service
        path = f"{request.node.name}/result.txt"
        data = "lorem ipsum dolor test_write_then_read_file á"
        bucket_name = "testingarchive20190210001"
        writing_result = storage.write_file(bucket_name, path, data)
        assert writing_result
        deletion_result = storage.delete_file(bucket_name, path)
        assert deletion_result is True
        with pytest.raises(FileNotInStorageError):
            storage.read_file(bucket_name, path)

    def test_delete_file_doesnt_exist(self, request, codecov_vcr, storage_service):
        storage = storage_service
        path = f"{request.node.name}/result.txt"
        bucket_name = "testingarchive20190210001"
        with pytest.raises(FileNotInStorageError):
            storage.delete_file(bucket_name, path)
