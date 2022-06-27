import pytest

from shared.encryption.token import decode_token, encode_token


@pytest.mark.parametrize(
    "input, expected",
    [
        ({"key": "some_key"}, "some_key"),
        ({"key": "some_key", "secret": "some_secret"}, "some_key:some_secret"),
        (
            {
                "key": "some_key",
                "secret": "some_secret",
                "refresh_token": "refresh",
            },
            "some_key:some_secret:refresh",
        ),
        (
            {"key": "some_key", "refresh_token": "refresh"},
            "some_key: :refresh",
        ),
    ],
)
def test_encode_access_token(input, expected):
    assert encode_token(input) == expected


@pytest.mark.parametrize(
    "input, expected",
    [
        ("some_key", {"key": "some_key", "secret": None}),
        ("some_key:some_secret", {"key": "some_key", "secret": "some_secret"}),
        (
            "some_key:some_secret:refresh",
            {"key": "some_key", "secret": "some_secret", "refresh_token": "refresh"},
        ),
        (
            "some_key: :refresh",
            {"key": "some_key", "secret": None, "refresh_token": "refresh"},
        ),
    ],
)
def test_decode_access_token(input, expected):
    assert decode_token(input) == expected


def test_decode_encode_access_token():
    token = {
        "key": "some_key",
        "secret": "some_secret",
        "refresh_token": "refresh",
    }
    assert decode_token(encode_token(token)) == token
