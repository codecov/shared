from cerberus import Validator

from shared.validation.helpers import (
    BranchSchemaField,
    CoverageRangeSchemaField,
    CustomFixPathSchemaField,
    LayoutStructure,
    PathPatternSchemaField,
    PercentSchemaField,
    UserGivenBranchRegex,
    UserGivenSecret,
    Invalid,
)


class CodecovYamlValidator(Validator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._show_secret = kwargs.get("show_secret", False)

    def _normalize_coerce_secret(self, value: str) -> str:
        """
            Coerces secret to normal value
        """
        if self._show_secret:
            return UserGivenSecret(self._show_secret).validate(value)
        return value

    def _normalize_coerce_regexify_path_pattern(self, value):
        return PathPatternSchemaField().validate(value)

    def _normalize_coerce_regexify_path_fix(self, value):
        return CustomFixPathSchemaField().validate(value)

    def _normalize_coerce_branch_name(self, value):
        return UserGivenBranchRegex().validate(value)

    def _normalize_coerce_percentage_to_number(self, value):
        return PercentSchemaField().validate(value)

    def _normalize_coerce_string_to_range(self, value):
        return CoverageRangeSchemaField().validate(value)

    def _normalize_coerce_branch_normalize(self, value):
        return BranchSchemaField().validate(value)

    def _validate_comma_separated_strings(self, constraint, field, value):
        """ Test the oddity of a value.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if constraint is True:
            try:
                LayoutStructure().validate(value)
            except Invalid as exc:
                self._error(field, exc.error_message)
