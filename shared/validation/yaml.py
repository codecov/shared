import logging

from shared.validation.exceptions import InvalidYamlException
from shared.validation.validator import CodecovYamlValidator
from shared.validation.user_schema import schema

log = logging.getLogger(__name__)

# *** Reminder: when changes are made to YAML validation, you will need to update the version of shared in both
# worker (to apply the changes) AND codecov-api (so the validate route reflects the changes) ***


def validate_yaml(inputted_yaml_dict, show_secrets=False):
    """Receives a dict containing the Codecov yaml provided by the user, validates and normalizes the fields for
        usage by other code.

    Args:
        inputted_yaml_dict (dict): The Codecov yaml as parsed by a yaml parser and turned into a dict
        show_secrets (boolean): indicates whether the validated yaml should show the decrypted versions of any encrypted values.
            worker sets this to true since we need to use these values, codecov-api sets this to false since the validate route is public and we
            don't want to unintentionally expose any sensitive user data.

    Returns: 
        (dict): A deep copy of the dict with the fields normalized

    Raises:
        InvalidYamlException: If the yaml inputted by the user is not valid
    """
    if not isinstance(inputted_yaml_dict, dict):
        raise InvalidYamlException([], "Yaml needs to be a dict")
    pre_process_yaml(inputted_yaml_dict)
    return validate_experimental(inputted_yaml_dict, show_secrets)


def post_process(validated_yaml_dict):
    """Does any needed post-processings

    Args:
        validated_yaml_dict (dict): The dict after validated

    Returns: 
        (dict): the post-processed dict to be used
    """
    return validated_yaml_dict


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


def validate_experimental(yaml_dict, show_secret):
    validator = CodecovYamlValidator(show_secret=show_secret)
    is_valid = validator.validate(yaml_dict, schema)
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
