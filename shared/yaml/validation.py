import binascii
import logging
from typing import Dict, List

from shared.encryption.yaml_secret import yaml_secret_encryptor
from shared.validation.cli_schema import schema as cli_schema
from shared.validation.exceptions import InvalidYamlException
from shared.validation.user_schema import schema as user_schema
from shared.validation.validator import CodecovYamlValidator

log = logging.getLogger(__name__)

YAML_TOP_LEVEL_RESERVED_KEYS: List[str] = [
    "to_string"  # Used to store the full YAML string preserving the original comments
]

# *** Reminder: when changes are made to YAML validation, you will need to update the version of shared in both
# worker (to apply the changes) AND codecov-api (so the validate route reflects the changes) ***


def validate_yaml(inputted_yaml_dict, show_secrets_for=None):
    """
        Receives a dict containing the Codecov yaml provided by the user, validates and normalizes
            the fields for usage by other code.

    Args:
        inputted_yaml_dict (dict): The Codecov yaml as parsed by a yaml parser and turned into a
            dict
        show_secrets_for (tuple): indicates a prefix for which we should show the decrypted
            versions of any encrypted values. `worker `sets this to the proper tuple since we need
            to use these values, codecov-api sets this to false since the validate
            route is public and we don't want to unintentionally expose any sensitive user data.

    Returns:
        (dict): A deep copy of the dict with the fields normalized

    Raises:
        InvalidYamlException: If the yaml inputted by the user is not valid
    """
    if not isinstance(inputted_yaml_dict, dict):
        raise InvalidYamlException([], "Yaml needs to be a dict")
    pre_process_yaml(inputted_yaml_dict)
    return do_actual_validation(inputted_yaml_dict, show_secrets_for)


def remove_reserved_keys(inputted_yaml_dict: Dict[str, any]) -> None:
    """
    This step removes reserved keywords in the base level of the json.
    If any YAML is trying to be processed and validated those reserved keys will be ignored
    """
    for key in YAML_TOP_LEVEL_RESERVED_KEYS:
        if key in inputted_yaml_dict:
            inputted_yaml_dict.pop(key)


def pre_process_yaml(inputted_yaml_dict):
    """
    Changes the inputted_yaml_dict in-place with compatibility changes that need to be done

    Args:
        inputted_yaml_dict (dict): The yaml dict inputted by the user
    """
    coverage = inputted_yaml_dict.get("coverage", {})
    if "flags" in coverage:
        inputted_yaml_dict["flags"] = coverage.pop("flags")
    if "parsers" in coverage:
        inputted_yaml_dict["parsers"] = coverage.pop("parsers")
    if "ignore" in coverage:
        inputted_yaml_dict["ignore"] = coverage.pop("ignore")
    if "fixes" in coverage:
        inputted_yaml_dict["fixes"] = coverage.pop("fixes")
    if inputted_yaml_dict.get("codecov") and inputted_yaml_dict["codecov"].get(
        "notify"
    ):
        if "require_ci_to_pass" in inputted_yaml_dict["codecov"]["notify"]:
            val = inputted_yaml_dict["codecov"]["notify"].pop("require_ci_to_pass")
            inputted_yaml_dict["codecov"]["require_ci_to_pass"] = val

    remove_reserved_keys(inputted_yaml_dict)


def _calculate_error_location_and_message_from_error_dict(error_dict):
    current_value, location_so_far = error_dict, []
    steps_done = 0
    # max depth to avoid being put in a loop
    while steps_done < 20:
        if isinstance(current_value, list) and len(current_value) > 0:
            current_value = current_value[0]
        if isinstance(current_value, dict) and len(current_value) > 0:
            first_key, first_value = next(iter((current_value.items())))
            location_so_far.append(first_key)
            current_value = first_value
        if isinstance(current_value, str):
            return location_so_far, current_value
        steps_done += 1
    return location_so_far, str(current_value)


class CodecovUserYamlValidator(CodecovYamlValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._show_secrets_for = kwargs.get("show_secrets_for", False)

    def _normalize_coerce_secret(self, value: str) -> str:
        """
        Coerces secret to normal value
        """
        if self._show_secrets_for:
            return UserGivenSecret(self._show_secrets_for).validate(value)
        return value


class UserGivenSecret(object):
    class InvalidSecret(Exception):
        pass

    encryptor = yaml_secret_encryptor

    def __init__(self, show_secrets_for):
        self.required_prefix = (
            "/".join(str(s) for s in show_secrets_for) if show_secrets_for else None
        )

    def validate(self, value):
        if not self.required_prefix:
            return value
        if value is not None and value.startswith("secret:"):
            try:
                res = self.decode(value, self.required_prefix)
                log.info(
                    "Valid secret was used by customer",
                    extra=dict(extra_data=self.required_prefix.split("/")),
                )
                return res
            except UserGivenSecret.InvalidSecret:
                return value
        return value

    @classmethod
    def encode(cls, value):
        return "secret:%s" % cls.encryptor.encode(value).decode()

    @classmethod
    def decode(cls, value, expected_prefix):
        try:
            decoded_value = cls.encryptor.decode(value[7:])
        except binascii.Error:
            raise UserGivenSecret.InvalidSecret()
        except ValueError:
            raise UserGivenSecret.InvalidSecret()
        if expected_prefix is not None and not decoded_value.startswith(
            expected_prefix
        ):
            raise UserGivenSecret.InvalidSecret()
        service, ownerid, repoid, clean_value = decoded_value.split("/", 3)
        return clean_value


def do_actual_validation(yaml_dict, show_secrets_for):
    validator = CodecovUserYamlValidator(show_secrets_for=show_secrets_for)
    full_schema = {**user_schema, **cli_schema}
    is_valid = validator.validate(yaml_dict, full_schema)
    if not is_valid:
        error_dict = validator.errors
        (
            error_location,
            error_message,
        ) = _calculate_error_location_and_message_from_error_dict(error_dict)
        raise InvalidYamlException(
            error_location=error_location,
            error_dict=error_dict,
            error_message=error_message,
        )
    return validator.document
