import binascii
from dataclasses import dataclass
from datetime import datetime
from json import loads

from shared.config import get_config
from shared.encryption.standard import EncryptorWithAlreadyGeneratedKey


@dataclass
class LicenseInformation(object):
    is_valid: bool = False
    is_trial: bool = False
    message: str = None
    url: str = None
    number_allowed_users: int = None
    number_allowed_repos: int = None
    expires: datetime = None
    is_pr_billing: bool = False


LICENSE_ERRORS_MESSAGES = {
    "invalid": "Enterprise license is invalid. Please contact Codecov team to renew license.",
    "no-license": "No license key found. Please contact enterprise@codecov.io to issue a license key. Thank you!",
    "unknown": "An unknown issue occured when checking your license. Please contact support.",
    "expired": "License has expired.",
    "demo-mode": "Currently in demo mode. No license key provided. Application restrictions apply.",
    "url-mismatch": "License url mismatch. If you have changed your codecov_url please contact staff to generate a new license key.",
    "users-exceeded": "Number of users exceeds license limit.",
    "repos-exceeded": "Number of repositories exceeds license limit.",
}


def load_raw_license_into_dict(raw_license):
    encryptor = EncryptorWithAlreadyGeneratedKey(
        b"\xfb\xe9\x1b4`\xff\xe2\xa1\xfa\xe3\xd0\xf9\x8d\xa6%\x7f"
    )
    return loads(encryptor.decode(raw_license))


def get_current_license():
    current_license = get_config("setup", "enterprise_license")
    if current_license is None:
        return LicenseInformation(
            is_valid=False, message=LICENSE_ERRORS_MESSAGES["no-license"]
        )
    return parse_license(current_license)


def parse_license(raw_license):
    try:
        license_dict = load_raw_license_into_dict(raw_license)
    except (binascii.Error, ValueError):
        return LicenseInformation(is_valid=False)
    number_allowed_users, number_allowed_repos = None, None
    if license_dict.get("users"):
        number_allowed_users = int(license_dict.get("users"))
    if license_dict.get("repos"):
        number_allowed_repos = int(license_dict.get("repos"))
    if license_dict.get("pr_billing"):
        is_pr_billing = bool(license_dict.get("pr_billing"))
    else:
        is_pr_billing = False
    return LicenseInformation(
        is_valid=True,
        message=None,
        url=license_dict.get("url"),
        number_allowed_users=number_allowed_users,
        number_allowed_repos=number_allowed_repos,
        expires=datetime.strptime(license_dict["expires"], "%Y-%m-%d %H:%M:%S"),
        is_trial=license_dict.get("trial"),
        is_pr_billing=is_pr_billing,
    )


def startup_license_logging():
    """
    Makes troubleshooting license issues easier - called by startup process in worker and api
    """
    if get_config("setup", "enterprise_license"):
        statements_to_print = [
            "",  # padding
            "==> Checking License",
        ]

        current_license = get_current_license()
        is_valid = current_license.is_valid
        statements_to_print.append(
            f"    License is {"valid" if is_valid else "INVALID"}"
        )

        if current_license.message:
            statements_to_print.append(f"    Warning: {current_license.message}")

        exp_date = current_license.expires
        statements_to_print.append(
            f"    License expires {datetime.strftime(exp_date, "%Y-%m-%d %H:%M:%S") if exp_date else "NOT FOUND"} <=="
        )
        statements_to_print.append("")  # padding

        # printing the message in a single statement so the lines won't get split up
        # among all the other messages during startup
        print(*statements_to_print, sep="\n")
