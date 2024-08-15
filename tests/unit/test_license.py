import json
from base64 import b64encode
from datetime import datetime
from unittest.mock import patch

from shared.encryption.standard import EncryptorWithAlreadyGeneratedKey
from shared.license import (
    LICENSE_ERRORS_MESSAGES,
    LicenseInformation,
    get_current_license,
    parse_license,
    startup_license_logging,
)
from tests.base import BaseTestCase

valid_trial_license_encrypted = "8rz8TfoZ1HDR5P2kpXSOaSvihqbHnJ4DANvDTB/J94tMjovTUUmuIX07W9FwB0UiiAp4j9McdH4JH5cloihjKqwluwC03t22/UA+4SHwxHbi6IhBbYXCEggYcrwtyjcdA4y3yARixGEsNEwDqAzxXLOe95nMetpb1u1Jr8E6CWp/2QSqvIUww8qTkegESk+3CiH3bPrA71pW8w9KYDX65g=="
invalid_license_encrypted = (
    "8rz8TfodsdsSOaSvih09nvnasu4DANvdsdsauIX07W9FwB0UiiAp4j9McdH4JH5cloihjKqadsada"
)


def test_sample_license_checking():
    encrypted_license = valid_trial_license_encrypted
    expected_result = LicenseInformation(
        is_valid=True,
        is_trial=True,
        message=None,
        url="https://codeov.mysite.com",
        number_allowed_users=None,
        number_allowed_repos=None,
        expires=datetime(2020, 5, 9, 0, 0),
    )
    assert parse_license(encrypted_license) == expected_result


def test_sample_license_pr_billing():
    """
    wxWEJyYgIcFpi6nBSyKQZQeaQ9Eqpo3SXyUomAqQOzOFjdYB3A8fFM1rm+kOt2ehy9w95AzrQqrqfxi9HJIb2zLOMOB9tSy52OykVCzFtKPBNsXU/y5pQKOfV7iI3w9CHFh3tDwSwgjg8UsMXwQPOhrpvl2GdHpwEhFdaM2O3vY7iElFgZfk5D9E7qEnp+WysQwHKxDeKLI7jWCnBCBJLDjBJRSz0H7AfU55RQDqtTrnR+rsLDHOzJ80/VxwVYhb
    License expires on 2021-01-01
    ---- Internal purposes only ----
    {'company': 'Test Company', 'expires': '2021-01-01 00:00:00', 'url': 'https://codecov.mysite.com', 'trial': False, 'users': 10, 'repos': None, 'pr_billing': True}
    """
    encrypted_license = "wxWEJyYgIcFpi6nBSyKQZQeaQ9Eqpo3SXyUomAqQOzOFjdYB3A8fFM1rm+kOt2ehy9w95AzrQqrqfxi9HJIb2zLOMOB9tSy52OykVCzFtKPBNsXU/y5pQKOfV7iI3w9CHFh3tDwSwgjg8UsMXwQPOhrpvl2GdHpwEhFdaM2O3vY7iElFgZfk5D9E7qEnp+WysQwHKxDeKLI7jWCnBCBJLDjBJRSz0H7AfU55RQDqtTrnR+rsLDHOzJ80/VxwVYhb"
    expected_result = LicenseInformation(
        is_valid=True,
        is_trial=False,
        message=None,
        url="https://codecov.mysite.com",
        number_allowed_users=10,
        is_pr_billing=True,
        number_allowed_repos=None,
        expires=datetime(2021, 1, 1, 0, 0),
    )
    assert parse_license(encrypted_license) == expected_result


def test_sample_license_checking_with_users_and_repos():
    encrypted_license = "0dRbhbzp8TVFQp7P4e2ES9lSfyQlTo8J7LQ/N51yeAE/KcRBCnU+QsVvVMDuLL4xNGXGGk9p4ZTmIl0II3cMr0tIoPHe9Re2UjommalyFYuP8JjjnNR/Ql2DnjOzEnTzsE2Poq9xlNHcIU4F9gC2WOYPnazR6U+t4CelcvIAbEpbOMOiw34nVyd3OEmWusquMNrwkNkk/lwjwCJmj6bTXQ=="
    expected_result = LicenseInformation(
        is_valid=True,
        is_trial=True,
        message=None,
        url="https://codeov.mysite.com",
        number_allowed_users=10,
        number_allowed_repos=20,
        expires=datetime(2020, 5, 10, 0, 0),
    )
    assert parse_license(encrypted_license) == expected_result


def test_invalid_license_checking_nonvalid_64encoded():
    encrypted_license = invalid_license_encrypted
    expected_result = LicenseInformation(
        is_valid=False,
        is_trial=False,
        message=None,
        url=None,
        number_allowed_users=None,
        number_allowed_repos=None,
        expires=None,
    )
    assert parse_license(encrypted_license) == expected_result


def test_invalid_license_checking_nonvalid_encrypted():
    encrypted_license = b64encode(b"suchabadlicense")
    expected_result = LicenseInformation(
        is_valid=False,
        is_trial=False,
        message=None,
        url=None,
        number_allowed_users=None,
        number_allowed_repos=None,
        expires=None,
    )
    assert parse_license(encrypted_license) == expected_result


def test_invalid_license_checking_wrong_key():
    a_good_value = {
        "users": None,
        "url": "https://codeov.mysite.com",
        "company": "name",
        "expires": "2020-05-09 00:00:00",
        "trial": True,
        "repos": None,
    }
    jsonified_good_value = json.dumps(a_good_value)
    wrong_key = b"\xe4n\n\xeb\xaa\xe6\x9d0\xed\xfaL\xe2c\x81h\xaf\xac*Pyq(H\xcc"
    wrong_encryptor = EncryptorWithAlreadyGeneratedKey(wrong_key)
    encrypted_license = wrong_encryptor.encode(jsonified_good_value)
    expected_result = LicenseInformation(
        is_valid=False,
        is_trial=False,
        message=None,
        url=None,
        number_allowed_users=None,
        number_allowed_repos=None,
        expires=None,
    )
    assert parse_license(encrypted_license) == expected_result


def test_get_current_license(mock_configuration):
    encrypted_license = valid_trial_license_encrypted
    mock_configuration.set_params({"setup": {"enterprise_license": encrypted_license}})
    expected_result = LicenseInformation(
        is_valid=True,
        is_trial=True,
        message=None,
        url="https://codeov.mysite.com",
        number_allowed_users=None,
        number_allowed_repos=None,
        expires=datetime(2020, 5, 9, 0, 0),
    )
    assert get_current_license() == expected_result


def test_get_current_license_no_license(mock_configuration):
    mock_configuration.set_params({"setup": None})
    expected_result = LicenseInformation(
        is_valid=False,
        is_trial=False,
        message="No license key found. Please contact enterprise@codecov.io to issue a license key. Thank you!",
        url=None,
        number_allowed_users=None,
        number_allowed_repos=None,
        expires=None,
    )
    assert get_current_license() == expected_result


@patch("builtins.print")
class TestUserGivenSecret(BaseTestCase):
    def test_startup_license_logging_valid(self, mock_print, mock_configuration):
        encrypted_license = valid_trial_license_encrypted
        mock_configuration.set_params(
            {"setup": {"enterprise_license": encrypted_license}}
        )

        expected_log = [
            "",
            "==> Checking License",
            "    License is valid",
            "    License expires 2020-05-09 00:00:00 <==",
            "",
        ]

        startup_license_logging()
        mock_print.assert_called_once_with(*expected_log, sep="\n")

    @patch("shared.license.parse_license")
    def test_startup_license_logging_invalid(
        self, mock_license_parsing, mock_print, mock_configuration
    ):
        mock_license_parsing.return_value = LicenseInformation(
            is_valid=False,
            message=LICENSE_ERRORS_MESSAGES["no-license"],
        )

        mock_configuration.set_params(
            {"setup": {"enterprise_license": True}}
        )  # value doesn't matter since parse_license is mocked

        expected_log = [
            "",
            "==> Checking License",
            "    License is INVALID",
            f"    Warning: {LICENSE_ERRORS_MESSAGES["no-license"]}",
            "    License expires NOT FOUND <==",
            "",
        ]

        startup_license_logging()
        mock_print.assert_called_once_with(*expected_log, sep="\n")
