from cerberus import Validator

from shared.validation.helpers import (
    BranchSchemaField,
    ByteSizeSchemaField,
    CoverageCommentRequirementSchemaField,
    CoverageRangeSchemaField,
    CustomFixPathSchemaField,
    Invalid,
    LayoutStructure,
    PathPatternSchemaField,
    PercentSchemaField,
    UserGivenBranchRegex,
)


class CodecovYamlValidator(Validator):
    def _normalize_coerce_secret(self, value: str) -> str:
        return value

    def _normalize_coerce_regexify_path_pattern(self, value):
        return PathPatternSchemaField().validate(value)

    def _normalize_coerce_regexify_path_fix(self, value):
        return CustomFixPathSchemaField().validate(value)

    def _normalize_coerce_branch_name(self, value):
        return UserGivenBranchRegex().validate(value)

    def _normalize_coerce_percentage_to_number(self, value):
        return PercentSchemaField().validate(value)

    def _normalize_coerce_percentage_to_number_or_auto(self, value):
        return PercentSchemaField().validate(value, allow_auto=True)

    def _normalize_coerce_string_to_range(self, value):
        return CoverageRangeSchemaField().validate(value)

    def _normalize_coerce_branch_normalize(self, value):
        return BranchSchemaField().validate(value)

    def _normalize_coerce_coverage_comment_required_changes(self, value):
        return CoverageCommentRequirementSchemaField().validate(value)

    def _normalize_coerce_byte_size(self, value):
        return ByteSizeSchemaField().validate(value)

    def _validate_comma_separated_strings(self, constraint, field, value):
        """Test the oddity of a value.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if constraint is True:
            try:
                LayoutStructure().validate(value)
            except Invalid as exc:
                self._error(field, exc.error_message)
