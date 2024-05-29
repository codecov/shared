import pytest

from shared.encryption.selector import DEFAULT_ENCRYPTOR_CONSTANT, EncryptorDivider
from shared.encryption.standard import StandardEncryptor


def test_encrypt_decrypt():
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: StandardEncryptor("legacy", "things"),
    }
    enc = EncryptorDivider(enc_dict, "abc")
    different_enc = EncryptorDivider(enc_dict, "abd")
    res_encode = enc.encode("mykey123456")
    assert res_encode.startswith(b"abc::")
    assert different_enc.decode(res_encode) == "mykey123456"


def test_decode_legacy_value():
    legacy_encryptor = StandardEncryptor("legacy", "things")
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor,
    }
    different_enc = EncryptorDivider(enc_dict, "abd")
    res_encode = legacy_encryptor.encode("mykey123456")
    assert b"::" not in res_encode
    assert different_enc.decode(res_encode) == "mykey123456"
    assert different_enc.decode(res_encode.decode()) == "mykey123456"


def test_encode_decode_all_from_divider():
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: StandardEncryptor("legacy", "things"),
    }
    enc = EncryptorDivider(enc_dict, DEFAULT_ENCRYPTOR_CONSTANT)
    different_enc = EncryptorDivider(enc_dict, "abd")
    res_encode = enc.encode("mykey123456")
    assert b"::" not in res_encode
    assert different_enc.decode(res_encode) == "mykey123456"


def test_init_bad_write_code():
    legacy_encryptor = StandardEncryptor("legacy", "things")
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor,
    }
    with pytest.raises(Exception, match="Encryption misconfigured on write code"):
        EncryptorDivider(enc_dict, "zzz")


def test_decrypt_token_legacy_generated():
    value = "jd3ewr8cndsbc-0wr$"
    legacy_encryptor = StandardEncryptor("aruba", "jamaica")
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor,
    }
    different_enc = EncryptorDivider(enc_dict, "abd")
    encoded = legacy_encryptor.encode(value)
    res = different_enc.decrypt_token(encoded)
    assert res == {"key": "jd3ewr8cndsbc-0wr$", "secret": None}


def test_decrypt_token_key_normal_generated():
    value = "jd3dsfsasq$^ewr8cndsbc-0wr$"
    legacy_encryptor = StandardEncryptor("aruba", "jamaica")
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor,
    }
    different_enc = EncryptorDivider(enc_dict, "abd")
    encoded = different_enc.encode(value)
    res = different_enc.decrypt_token(encoded)
    assert res == {"key": value, "secret": None}


def test_decrypt_token_key_normal_generated_with_secret_pair():
    value = "jd3dsfsasq$^ew:r8cndsbc-0wr$"
    legacy_encryptor = StandardEncryptor("aruba", "jamaica")
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor,
    }
    different_enc = EncryptorDivider(enc_dict, "abd")
    encoded = different_enc.encode(value)
    res = different_enc.decrypt_token(encoded)
    assert res == {"key": value.split(":")[0], "secret": value.split(":")[1]}


def test_decrypt_token_key_normal_generated_with_secret_pair_refresh():
    value = "jd3dsfsasq$^ew: :r8cndsbc-0wr$"
    legacy_encryptor = StandardEncryptor("aruba", "jamaica")
    enc_dict = {
        "abc": StandardEncryptor("part1"),
        "abd": StandardEncryptor("part1", "abd", "banana"),
        "plq": StandardEncryptor("r", "qwerty", "apple"),
        DEFAULT_ENCRYPTOR_CONSTANT: legacy_encryptor,
    }
    different_enc = EncryptorDivider(enc_dict, "abd")
    encoded = different_enc.encode(value)
    res = different_enc.decrypt_token(encoded)
    assert res == {
        "key": "jd3dsfsasq$^ew",
        "refresh_token": "r8cndsbc-0wr$",
        "secret": None,
    }
