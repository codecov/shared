from base64 import b64encode

from shared.yaml.validation import UserGivenSecret, validate_yaml
from tests.base import BaseTestCase


def test_show_secret_case():
    value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
    encoded_value = UserGivenSecret.encode(value)
    user_input = {
        "coverage": {
            "round": "down",
            "precision": 2,
            "range": [70.0, 100.0],
            "status": {"project": {"default": {"base": "auto"}}},
            "notify": {"irc": {"user_given_title": {"password": encoded_value}}},
        },
        "ignore": ["Pods/.*", "**/*bundle"],
    }
    expected_result = {
        "coverage": {
            "round": "down",
            "precision": 2,
            "range": [70.0, 100.0],
            "status": {"project": {"default": {"base": "auto"}}},
            "notify": {
                "irc": {
                    "user_given_title": {
                        "password": "https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
                    }
                }
            },
        },
        "ignore": ["Pods/.*", "(?s:.*/[^\\/]*bundle)\\Z"],
    }
    result = validate_yaml(
        user_input, show_secrets_for=("github", "11934774", "154468867")
    )
    assert result == expected_result


class TestUserGivenSecret(BaseTestCase):
    def test_simple_user_given_secret(self):
        value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        encoded_value = UserGivenSecret.encode(value)
        ugs = UserGivenSecret(show_secrets_for=("github", "11934774", "154468867"))
        assert ugs.validate(value) == value
        assert (
            ugs.validate(encoded_value)
            == "https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        )
        bad_ugs = UserGivenSecret(show_secrets_for=("github", "12345", "154468867"))
        assert bad_ugs.validate(value) == value
        assert bad_ugs.validate(encoded_value) == encoded_value

    def test_simple_user_given_secret_rotated_key(self):
        encoded_data = "secret:v1::zsV9A8pHadNle357DGJHbZCTyCYA+TXdUd9TN3IY2DIWcPOtgK3Pg1EgA6OZr9XJ1EsdpL765yWrN4pfR3elRdN2LUwiuv6RkNjpbiruHx45agsgxdu8fi24p5pkCLvjcW0HqdH2PTvmHauIp+ptgA=="
        ugs = UserGivenSecret(show_secrets_for=("github", 11934774, 154468867))
        assert (
            ugs.validate(encoded_data)
            == "https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        )

    def test_pseudosecret_user_given_secret(self):
        value = "secret:arriba"
        ugs = UserGivenSecret(show_secrets_for=("github", "12", 98))
        assert ugs.validate(value) == value

    def test_b64encoded_pseudosecret_user_given_secret(self):
        encoded_value = b64encode("arriba".encode())
        value = b"secret:" + encoded_value
        value = value.decode()
        ugs = UserGivenSecret(show_secrets_for=("github", "12", 98))
        assert ugs.validate(value) == value

    def test_simple_user_dont_show_secret(self):
        value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        encoded_value = UserGivenSecret.encode(value)
        ugs = UserGivenSecret(show_secrets_for=None)
        assert ugs.validate(value) == value
        assert ugs.validate(encoded_value) == encoded_value
