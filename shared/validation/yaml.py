import logging
import random
import os

from voluptuous import (
    Schema,
    Optional,
    MultipleInvalid,
    Or,
    And,
    Match,
    Range,
    Length,
    Inclusive,
    Msg,
)
from shared.validation.exceptions import InvalidYamlException
from shared.validation.helpers import (
    PercentSchemaField,
    BranchSchemaField,
    UserGivenBranchRegex,
    LayoutStructure,
    PathPatternSchemaField,
    UserGivenSecret,
    CoverageRangeSchemaField,
    CustomFixPathSchemaField,
)
from shared.validation.experimental import validate_experimental

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
