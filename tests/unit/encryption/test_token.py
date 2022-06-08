from shared.encryption.token import decode_token, encode_token


def test_encode_access_token():
    token = {"access_token": "some_key"}
    assert encode_token(token) == "some_key"
    token["secret"] = "some_secret"
    assert encode_token(token) == "some_key:some_secret"
    token["refresh_token"] = "refresh"
    assert encode_token(token) == "some_key:some_secret:refresh"
    token["secret"] = None
    assert encode_token(token) == "some_key: :refresh"


def test_decode_access_token():
    token = {"key": "some_key", "secret": None}
    assert decode_token("some_key") == token
    token["secret"] = "some_secret"
    assert decode_token("some_key:some_secret") == token
    token["refresh_token"] = "refresh"
    assert decode_token("some_key:some_secret:refresh") == token
    token["secret"] = None
    assert decode_token("some_key: :refresh") == token
