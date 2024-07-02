import functools
import logging
import numbers
import re
from typing import Any, List

import pyparsing as pp

from shared.validation.types import (
    CoverageCommentRequiredChanges,
    CoverageCommentRequiredChangesANDGroup,
    CoverageCommentRequiredChangesORGroup,
    ValidRawRequiredChange,
)

log = logging.getLogger(__name__)


class Invalid(Exception):
    def __init__(self, error_message):
        super().__init__()
        self.error_message = error_message


class CoverageRangeSchemaField(object):
    """
    Pattern for the user to input a range like 60..90 (which means from 60 to 90)

    We accept ".." and "..." as separators

    This value is converted into a two members array

    CoverageRangeSchemaField().validate('30...99') == [30.0, 99.0]
    """

    def validate_bounds(self, lower_bound, upper_bound):
        if not 0 <= lower_bound <= 100:
            raise Invalid(f"Lower bound {lower_bound} should be between 0 and 100")
        if not 0 <= upper_bound <= 100:
            raise Invalid(f"Upper bound {upper_bound} should be between 0 and 100")
        if lower_bound > upper_bound:
            raise Invalid(
                f"Upper bound {upper_bound} should be bigger than {lower_bound}"
            )
        return [lower_bound, upper_bound]

    def validate(self, data):
        if isinstance(data, list):
            if len(data) != 2:
                raise Invalid(f"{data} should have only two elements")
            try:
                lower_bound, upper_bound = sorted(float(el) for el in data)
                return self.validate_bounds(lower_bound, upper_bound)
            except ValueError:
                raise Invalid(f"{data} should have numbers as the range limits")
        if "...." in data:
            raise Invalid(f"{data} should have two or three dots, not four")
        elif "..." in data:
            splitter = "..."
        elif ".." in data:
            splitter = ".."
        else:
            raise Invalid(f"{data} does not have the correct format")
        split_value = data.split(splitter)
        if len(split_value) != 2:
            raise Invalid(f"{data} should have only two numbers")
        try:
            lower_bound = float(split_value[0])
            upper_bound = float(split_value[1])
            return self.validate_bounds(lower_bound, upper_bound)
        except ValueError:
            raise Invalid(f"{data} should have numbers as the range limits")


class CoverageCommentRequirementSchemaField(object):
    """Converts `comment.require_changes` into CoverageCommentRequiredChanges

    Conversion table:
        False -> CoverageCommentRequiredChanges.no_requirements
        True -> CoverageCommentRequiredChanges.any_change
        "any_change" -> CoverageCommentRequiredChanges.any_change
        "coverage_drop" -> CoverageCommentRequiredChanges.coverage_drop
        "uncovered_patch" -> CoverageCommentRequiredChanges.uncovered_patch

    We also accept AND and OR operators
    """

    def validate(self, data: Any) -> CoverageCommentRequiredChangesANDGroup:
        """Validates and coerces values into CoverageCommentRequiredChanges

        raises: Invalid
        """
        if isinstance(data, bool):
            return self.validate_bool(data)
        elif isinstance(data, str):
            return self.validate_str(data)
        raise Invalid("Only bool and str are accepted values")

    def validate_bool(self, data: bool) -> CoverageCommentRequiredChangesANDGroup:
        if data:
            return [CoverageCommentRequiredChanges.any_change.value]
        return [CoverageCommentRequiredChanges.no_requirements.value]

    def _convert_to_binary_value(
        self, valid_requirement: ValidRawRequiredChange
    ) -> int:
        """Gets the binary value of `valid_requirement` as defined in CoverageCommentRequiredChanges"""
        return CoverageCommentRequiredChanges[valid_requirement].value

    def _parse_or_group(
        self, acc: int, value: ValidRawRequiredChange
    ) -> CoverageCommentRequiredChangesORGroup:
        """Combines the individual `valid_requirement` into a single value"""
        return acc | self._convert_to_binary_value(value)

    def validate_str(self, data: str) -> CoverageCommentRequiredChangesANDGroup:
        """Validates required_changes from a string that represents operations on valid_requirements
        and returns the result.

        Result is CoverageCommentRequiredChangesANDGroup, a list of ORGroups.
        An ORGroup is 1 or more valid_requirements that are grouped together (using OR operations)
        For the overall ANDGroup to be satisfied, ALL the ORGroups that are port of it need to also be satisfied.
        """
        if data == "":
            raise Invalid("required_changes is empty")
        data = data.lower()

        valid_requirements = pp.oneOf(
            "coverage_drop uncovered_patch any_change", asKeyword=True
        )
        or_groups_parser = pp.delimitedList(valid_requirements, "or").setResultsName(
            "or_groups", listAllMatches=True
        )
        and_groups_parser = pp.delimitedList(or_groups_parser, "and")

        try:
            raw_or_groups: List[pp.ParseResults] = and_groups_parser.parseString(
                data, parseAll=True
            )["or_groups"]
            parsed_or_groups = [
                functools.reduce(self._parse_or_group, raw_group, 0)
                for raw_group in raw_or_groups
            ]
            return parsed_or_groups

        except pp.ParseException:
            raise Invalid("Failed to parse required_changes")


class ByteSizeSchemaField(object):
    """Converts a possible string with byte extension size into integer with number of bytes.
    Acceptable extensions are 'mb', 'kb', 'gb', 'b' and 'bytes' (case insensitive).
    Also accepts integers, returning the value itself as the number of bytes.

    Example:
        100 -> 100
        "100b" -> 100
        "100 mb" -> 100000000
        "12KB" -> 12000
    """

    def _validate_str(self, data: str) -> int:
        data = data.lower()
        regex = re.compile(r"^(\d+)\s*(mb|kb|gb|b|bytes)$")
        match = regex.match(data)
        if match is None:
            raise Invalid(
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes"
            )
        size, extension = match.groups()
        extension_multiplier = {"b": 1, "bytes": 1, "kb": 1e3, "mb": 1e6, "gb": 1e9}
        return int(size) * extension_multiplier[extension]

    def validate(self, data: Any) -> int:
        if isinstance(data, int):
            return data
        if isinstance(data, str):
            return self._validate_str(data)
        raise Invalid(f"Value should be int or str. Received {type(data).__name__}")


class PercentSchemaField(object):
    """
    A field for percentages. Accepts both with and without % symbol.
    The end result is the percentage number

    PercentSchemaField().validate('60%') == 60.0
    """

    field_regex = re.compile(r"(\d+)(\.\d+)?%?")

    def validate(self, value, allow_auto=False):
        if value == "auto" and allow_auto:
            return value
        elif value == "auto":
            raise Invalid("This field does not accept auto")
        if isinstance(value, numbers.Number):
            return float(value)
        if not self.field_regex.match(value):
            raise Invalid(f"{value} should be a number")
        if value.endswith("%"):
            value = value.rstrip("%")
        try:
            return float(value)
        except ValueError:
            raise Invalid(f"{value} should be a number")


def determine_path_pattern_type(filepath_pattern):
    """
        Tries to determine whether `filepath_pattern` is a:
            - 'path_prefix'
            - 'glob'
            - 'regex'

        As you can see in the documentation for PathPatternSchemaField,
            the same pattern can be used as more than one way.

    Args:
        filepath_pattern (str): the filepath

    Returns:
        str: The probable type of that inputted pattern
    """
    reserved_chars = ["*", "$", "]", "["]
    if not any(x in filepath_pattern for x in reserved_chars):
        return "path_prefix"
    if "**" in filepath_pattern or "/*" in filepath_pattern:
        return "glob"
    expected_regex_star_cases = ["]*", ".*"]
    if "*" in filepath_pattern and not any(
        x in filepath_pattern for x in expected_regex_star_cases
    ):
        return "glob"
    try:
        re.compile(filepath_pattern)
        return "regex"
    except re.error:
        return "glob"


def translate_glob_to_regex(pat, end_of_string=True):
    """
    Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.

    This is copied from fnmatch.translate_glob_to_regex. If you could be
        so kind and see if they changed it since we copied,
        that would be very helpful, thanks.

    The only reason we copied (instead of importing and using),
        is that we needed to change behavior on **
    """

    i, n = 0, len(pat)
    res = ""
    while i < n:
        c = pat[i]
        i = i + 1
        if c == "*":
            if i < n and pat[i] == "*":
                res = res + ".*"
                i = i + 1
            else:
                res = res + r"[^\/]*"
        elif c == "?":
            res = res + "."
        elif c == "[":
            j = i
            if j < n and pat[j] == "!":
                j = j + 1
            if j < n and pat[j] == "]":
                j = j + 1
            while j < n and pat[j] != "]":
                j = j + 1
            if j >= n:
                res = res + "\\["
            else:
                stuff = pat[i:j]
                if "--" not in stuff:
                    stuff = stuff.replace("\\", r"\\")
                else:
                    chunks = []
                    k = i + 2 if pat[i] == "!" else i + 1
                    while True:
                        k = pat.find("-", k, j)
                        if k < 0:
                            break
                        chunks.append(pat[i:k])
                        i = k + 1
                        k = k + 3
                    chunks.append(pat[i:j])
                    # Escape backslashes and hyphens for set difference (--).
                    # Hyphens that create ranges shouldn't be escaped.
                    stuff = "-".join(
                        s.replace("\\", r"\\").replace("-", r"\-") for s in chunks
                    )
                # Escape set operations (&&, ~~ and ||).
                stuff = re.sub(r"([&~|])", r"\\\1", stuff)
                i = j + 1
                if stuff[0] == "!":
                    stuff = "^" + stuff[1:]
                elif stuff[0] in ("^", "["):
                    stuff = "\\" + stuff
                res = "%s[%s]" % (res, stuff)
        else:
            res = res + re.escape(c)
    if end_of_string:
        return r"(?s:%s)\Z" % res
    return r"(?s:%s)" % res


class PathPatternSchemaField(object):
    """This class holds the logic for validating and processing a user given path pattern

    This is how it works. The intention is to allow the user to give a string as an input,
        and in return, that string is used as a pattern to identify which paths to include/exclude
        from their report

    For that, we take the user input, and transform it into a regex that python can process

    The user can input three types of patterns:

        - path_prefix - It's when user inputs something like `path/to/folder`.
            That means that, every filename for a file that lives inside `path/to/folder`
                will match that pattern, regardless of how deep it is.
        - regex - The user inputs a regex directly. In this case we simply apply the regex to the
            filepath to see if it matches
        - glob - The user inputs a glob (as the glob that we use in unix, using `*` and `**`)

    This class tries to determine which type of pattern the user inputted. We say "try", because
        some paths can be more than one type, and we try our best to see what the user meant.

    For example, `a.*` could match `a/folder1/path/file.py` as a regex, but not as a glob.
        As a glob, `a.*` could match a.yaml, a.py and a.cpp

    After determined the type, the code converts that type of pattern to a regex (in case
        the user inputted a regex, it is used as it is)

    One additional processing we do is to account for the usage of `!` by the user.
        `!` means negation, and although we support `ignore` fields, sometimes the users
        prefer to just use `!` to denote something they want to exclude.

    To see some examples of results from this validator field, take a look at
        services/yaml/tests/test_validation.py::TestPathPatternSchemaField
    """

    def input_type(self, value):
        return determine_path_pattern_type(value)

    def validate_glob(self, value):
        if not value.endswith("$") and not value.endswith("*"):
            log.warning("Old glob behavior would have interpreted this glob as prefix")
        return translate_glob_to_regex(value)

    def validate_path_prefix(self, value):
        return f"^{value}.*"

    def validate(self, value):
        if value.startswith("!"):
            is_negative = True
            value = value.lstrip("!")
        else:
            is_negative = False

        if value.startswith("./"):
            value = value[2:]

        input_type = self.input_type(value)
        result = self.validate_according_to_type(input_type, value)
        if is_negative:
            return f"!{result}"
        return result

    def validate_according_to_type(self, input_type, value):
        if input_type == "regex":
            try:
                re.compile(value)
                return value
            except re.error:
                raise Invalid(f"{value} does not work as a regex")
        elif input_type == "glob":
            return self.validate_glob(value)
        elif input_type == "path_prefix":
            return self.validate_path_prefix(value)
        else:
            raise Invalid(f"We did not detect what {value} is")


class CustomFixPathSchemaField(object):
    def input_type(self, value):
        return determine_path_pattern_type(value)

    def validate(self, value):
        if "::" not in value:
            raise Invalid("Pathfix must split before and after with a ::")
        before, after = value.split("::", 1)
        if before == "" or after == "":
            return value
        before_input_type = self.input_type(before)
        before = self.validate_according_to_type(before_input_type, before)
        return f"{before}::{after}"

    def validate_according_to_type(self, input_type, value):
        if input_type == "regex":
            try:
                re.compile(value)
                return value
            except re.error:
                raise Invalid(f"{value} does not work as a regex")
        elif input_type == "glob":
            return translate_glob_to_regex(value, end_of_string=False)
        elif input_type == "path_prefix":
            return f"^{value}"
        else:
            raise Invalid(f"We did not detect what {value} is")


class UserGivenBranchRegex(object):
    asterisk_to_regexp = re.compile(r"(?<!\.)\*")

    def validate(self, value):
        if value is None:
            return None
        if value in ("*", "", None, ".*"):
            return ".*"
        else:
            # apple* => apple.*
            nv = self.asterisk_to_regexp.sub(".*", value.strip())
            if not nv.startswith((".*", "^")):
                nv = "^%s" % nv
            if not nv.endswith((".*", "$")):
                nv = "%s$" % nv
            re.compile(nv)
            return nv


class LayoutStructure(object):
    acceptable_objects = set(
        [
            "changes",
            "diff",
            "file",
            "files",
            "flag",
            "flags",
            "footer",
            "header",
            "reach",
            "components",
            "suggestions",
            "betaprofiling",
            "sunburst",
            "tree",
            "uncovered",
            "newheader",  # deprecated, keeping it for backward compatibility
            "newfooter",  # deprecated, keeping it for backward compatibility
            "feedback",
            "newfiles",  # deprecated, keeping it for backward compatibility
            "condensed_header",
            "condensed_footer",
            "condensed_files",
        ]
    )

    def validate(self, value):
        values = value.split(",")
        actual_values = [x.strip().split(":")[0] for x in values if x != ""]
        if not set(actual_values) <= self.acceptable_objects:
            extra_objects = set(actual_values) - self.acceptable_objects
            extra_objects = ",".join(sorted(extra_objects))
            raise Invalid(f"Unexpected values on layout: {extra_objects}")
        for val in values:
            if ":" in val:
                try:
                    int(val.strip().split(":")[1])
                except ValueError:
                    raise Invalid(
                        f"Improper pattern for value on layout: {val.strip()}"
                    )
        return value


class BranchSchemaField(object):
    def validate(self, value):
        if not isinstance(value, str):
            raise Invalid(f"Branch must be {str}, was {type(value)} ({value})")
        if value[:7] == "origin/":
            return value[7:]
        elif value[:11] == "refs/heads/":
            return value[11:]
        return value
