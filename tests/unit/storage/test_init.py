from shared.rollouts.features import USE_NEW_MINIO
from shared.storage import get_appropriate_storage_service
from shared.storage.aws import AWSStorageService
from shared.storage.fallback import StorageWithFallbackService
from shared.storage.gcp import GCPStorageService
from shared.storage.minio import MinioStorageService
from shared.storage.new_minio import NewMinioStorageService

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
    "aws_secret_access_key": "Rb5ky+vMTpbJX/dFVQA4r7m84zGrL44KpeoPxtD0",
    "region_name": "us-east-1",
}

minio_config = {
    "access_key_id": "codecov-default-key",
    "secret_access_key": "codecov-default-secret",
    "verify_ssl": False,
    "host": "minio",
    "port": "9000",
    "iam_auth": False,
    "iam_endpoint": None,
}


class TestStorageInitialization(object):
    def test_get_appropriate_storage_service_fallback(self, mock_configuration):
        mock_configuration.params["services"] = {
            "chosen_storage": "gcp_with_fallback",
            "gcp": gcp_config,
            "aws": aws_config,
        }
        res = get_appropriate_storage_service()
        assert isinstance(res, StorageWithFallbackService)
        assert isinstance(res.main_service, GCPStorageService)
        assert res.main_service.config == gcp_config
        assert isinstance(res.fallback_service, AWSStorageService)
        assert res.fallback_service.config == aws_config

    def test_get_appropriate_storage_service_aws(self, mock_configuration):
        mock_configuration.params["services"] = {
            "chosen_storage": "aws",
            "gcp": gcp_config,
            "aws": aws_config,
        }
        res = get_appropriate_storage_service()
        assert isinstance(res, AWSStorageService)
        assert res.config == aws_config

    def test_get_appropriate_storage_service_gcp(self, mock_configuration):
        mock_configuration.params["services"] = {
            "chosen_storage": "gcp",
            "gcp": gcp_config,
            "aws": aws_config,
        }
        res = get_appropriate_storage_service()
        assert isinstance(res, GCPStorageService)
        assert res.config == gcp_config

    def test_get_appropriate_storage_service_minio(self, mock_configuration):
        mock_configuration.params["services"] = {
            "chosen_storage": "minio",
            "gcp": gcp_config,
            "aws": aws_config,
            "minio": minio_config,
        }
        res = get_appropriate_storage_service()
        assert isinstance(res, MinioStorageService)
        assert res.minio_config == minio_config

    def test_get_appropriate_storage_service_new_minio(
        self, mock_configuration, mocker
    ):
        mock_configuration.params["services"] = {
            "chosen_storage": "minio",
            "gcp": gcp_config,
            "aws": aws_config,
            "minio": minio_config,
        }
        mocker.patch.object(USE_NEW_MINIO, "check_value", return_value=True)
        res = get_appropriate_storage_service(repoid=123)
        assert isinstance(res, NewMinioStorageService)
        assert res.minio_config == minio_config

    def test_get_appropriate_storage_service_new_minio_false(
        self, mock_configuration, mocker
    ):
        mock_configuration.params["services"] = {
            "chosen_storage": "minio",
            "gcp": gcp_config,
            "aws": aws_config,
            "minio": minio_config,
        }
        mocker.patch.object(USE_NEW_MINIO, "check_value", return_value=False)
        res = get_appropriate_storage_service(repoid=123)
        assert isinstance(res, MinioStorageService)
        assert res.minio_config == minio_config
