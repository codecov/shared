from shared.encryption.oauth import get_encryptor_from_configuration
from shared.encryption.selector import EncryptorDivider
from shared.encryption.standard import StandardEncryptor


def test_get_encryptor_from_configuration_nothing_new(mock_configuration):
    res = get_encryptor_from_configuration()
    assert isinstance(res, EncryptorDivider)
    assert sorted(res._encryptor_mapping.keys()) == ["default_enc"]
    assert all(
        isinstance(x, StandardEncryptor) for x in res._encryptor_mapping.values()
    )
    string_to_encode = "supercaliforgettherest"
    encoded = res.encode(string_to_encode)
    assert b"::" not in encoded
    assert res.decode(encoded) == string_to_encode


def test_get_encryptor_from_configuration_full_thing(mock_configuration):
    mock_configuration._params["setup"]["encryption"] = {
        "keys": [
            {"name": "abc", "value": "84wvnuiho2%^Q(DIHD"},
            {"name": "def", "value": "somerandomstring_(+"},
            {"name": "ghi", "value": "i3uc8s3u%^Qdsda(ads"},
        ],
        "write_key": "abc",
    }
    res = get_encryptor_from_configuration()
    assert isinstance(res, EncryptorDivider)
    assert sorted(res._encryptor_mapping.keys()) == [
        "default_enc",
        "v1_abc",
        "v1_def",
        "v1_ghi",
    ]
    assert all(
        isinstance(x, StandardEncryptor) for x in res._encryptor_mapping.values()
    )
    string_to_encode = "supercaliforgettherest"
    encoded = res.encode(string_to_encode)
    assert b"::" in encoded
    assert encoded.startswith(b"v1_abc")
    assert res.decode(encoded) == string_to_encode
