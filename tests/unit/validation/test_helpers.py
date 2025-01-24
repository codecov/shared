import re

import pytest

from shared.validation.helpers import (
    BundleSizeThresholdSchemaField,
    ByteSizeSchemaField,
    CoverageCommentRequirementSchemaField,
    CoverageRangeSchemaField,
    CustomFixPathSchemaField,
    Invalid,
    LayoutStructure,
    PathPatternSchemaField,
    PercentSchemaField,
    UserGivenBranchRegex,
    determine_path_pattern_type,
    translate_glob_to_regex,
)
from shared.yaml.validation import pre_process_yaml
from tests.base import BaseTestCase


class TestPathPatternSchemaField(BaseTestCase):
    def test_simple_path_structure_no_star(self):
        ps = PathPatternSchemaField()
        res = ps.validate("a/b")
        compiled = re.compile(res)
        assert compiled.match("a/b") is not None
        assert compiled.match("a/b/file_1.py") is not None
        assert compiled.match("c/a/b") is None
        assert compiled.match("a/path/b") is None
        assert compiled.match("a/path/path2/b") is None

    def test_simple_path_structure_regex(self):
        ps = PathPatternSchemaField()
        res = ps.validate("[a-z]+/test_.*")
        compiled = re.compile(res)
        assert compiled.match("perro/test_folder.py") is not None
        assert compiled.match("cachorro/test_folder.py") is not None
        assert compiled.match("cachorro/tes_folder.py") is None
        assert compiled.match("cachorro/what/test_folder.py") is None
        assert compiled.match("[/a/b") is None

    def test_simple_path_structure_one_star_end(self):
        ps = PathPatternSchemaField()
        res = ps.validate("tests/*")
        compiled = re.compile(res)
        assert compiled.match("tests/file_1.py") is not None
        assert compiled.match("tests/testeststsetetesetsfile_2.py") is not None
        assert compiled.match("tests/deep/file_1.py") is None

    def test_simple_path_structure_one_star(self):
        ps = PathPatternSchemaField()
        res = ps.validate("a/*/b")
        compiled = re.compile(res)
        assert compiled.match("a/path/b") is not None
        assert compiled.match("a/path/b/file_2.py") is None
        assert compiled.match("a/path/b/more_path/some_file.py") is None
        assert compiled.match("a/b") is None
        assert compiled.match("a/path/path2/b") is None

    def test_simple_path_structure_negative(self):
        ps = PathPatternSchemaField()
        res = ps.validate("!path/to/folder")
        assert res.startswith("!")
        compiled = re.compile(res[1:])
        # Check the negatives, we want `path/to/folder` files to match so we refuse them later
        assert compiled.match("path/to/folder") is not None
        assert compiled.match("path/to/folder/file_2.py") is not None
        assert compiled.match("path/to/folder/more_path/some_file.py") is not None
        assert compiled.match("a/b") is None
        assert compiled.match("path/folder") is None

    def test_simple_path_structure_double_star(self):
        ps = PathPatternSchemaField()
        res = ps.validate("a/**/b")
        compiled = re.compile(res)
        assert compiled.match("a/path/b") is not None
        assert compiled.match("a/path/b/some_file.py") is None
        assert compiled.match("a/path/b/more_path/some_file.py") is None
        assert compiled.match("a/path/path2/b") is not None
        assert compiled.match("a/path/path2/b/some_file.py") is None
        assert compiled.match("a/path/path2/b/more_path/some_file.py") is None
        assert compiled.match("a/c") is None

    def test_path_with_leading_period_slash(self):
        ps = PathPatternSchemaField()
        res = ps.validate("./src/register-test-globals.ts")
        compiled = re.compile(res)
        assert compiled.match("src/register-test-globals.ts") is not None
        second_res = ps.validate("./test/*.cc")
        second_compiled = re.compile(second_res)
        assert second_compiled.match("test/test_SW_Markov.cc") is not None

    def test_star_dot_star_pattern(self):
        ps = PathPatternSchemaField()
        res = ps.validate("test/**/*.*")
        compiled = re.compile(res)
        assert compiled.match("test/unit/presenters/goal_sparkline_test.rb") is not None

    def test_double_star_end(self):
        user_input = "Snapshots/**"
        ps = PathPatternSchemaField()
        res = ps.validate(user_input)
        compiled = re.compile(res)
        assert compiled.match("Snapshots/Snapshots/ViewController.swift") is not None

    def test_double_star_prefix(self):
        user_input = "**/*bundle"
        ps = PathPatternSchemaField()
        res = ps.validate(user_input)
        compiled = re.compile(res)
        paths_to_match = [
            "app/Bundle/ignoreme.bundle",
            "tests/test_bundle/sample_bundle",
        ]
        paths_not_to_match = [
            "app/Bundle/BundleCart.py",
            "app/Bundle/__init__.py",
            "app/Bundle/mybundle.py",
            "tests/test_bundle/test_bundle_cart.py",
        ]
        for path in paths_to_match:
            assert compiled.match(path) is not None
        for path in paths_not_to_match:
            assert compiled.match(path) is None


class TestLayoutStructure(BaseTestCase):
    def test_simple_layout(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, files, components, footer"
        expected_result = "reach, diff, flags, files, components, footer"
        assert expected_result == schema.validate(result)

    def test_empty_layout(self):
        schema = LayoutStructure()
        layout_input = ""
        expected_result = ""
        assert expected_result == schema.validate(layout_input)

    def test_simple_layout_with_number(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, files:10, footer"
        expected_result = "reach, diff, flags, files:10, footer"
        assert expected_result == schema.validate(result)

    def test_simple_layout_with_improper_number(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, files:twenty, footer"
        with pytest.raises(Invalid) as exc:
            schema.validate(result)
        assert (
            exc.value.error_message
            == "Improper pattern for value on layout: files:twenty"
        )

    def test_simple_layout_bad_name(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, love, files, footer"
        with pytest.raises(Invalid) as exc:
            schema.validate(result)
        assert exc.value.error_message == "Unexpected values on layout: love"


class TestCoverageRangeSchemaField(BaseTestCase):
    def test_simple_coverage_range(self):
        crsf = CoverageRangeSchemaField()
        assert crsf.validate([80, 90]) == [80.0, 90.0]
        assert crsf.validate("80..90") == [80.0, 90.0]
        assert crsf.validate("80...90") == [80.0, 90.0]
        assert crsf.validate("80...100") == [80.0, 100.0]
        invalid_cases = [
            "80....90",
            "80.90",
            "90..80",
            "90..80..50",
            "infinity...90",
            "80...?90",
            "80...101",
            "-80...90",
            "80...9f0",
            ["arroba", 90],
            [10, 20, 30],
            [10, 20, 30],
            ["infinity", 90],
        ]
        for invalid in invalid_cases:
            with pytest.raises(Invalid):
                crsf.validate(invalid)


class TestUserGivenBranchRegex(BaseTestCase):
    def test_user_givne_branch(self):
        a = UserGivenBranchRegex()
        assert a.validate(None) is None
        assert a.validate(".*") == ".*"
        assert a.validate("*") == ".*"
        assert a.validate("apple*") == "^apple.*"
        assert a.validate("apple") == "^apple$"


class TestPercentSchemaField(BaseTestCase):
    def test_simple_coverage_range(self):
        crsf = PercentSchemaField()
        assert crsf.validate(80) == 80.0
        assert crsf.validate("auto", allow_auto=True) == "auto"
        assert crsf.validate(80.0) == 80.0
        assert crsf.validate("80%") == 80.0
        assert crsf.validate("80") == 80.0
        assert crsf.validate("0") == 0.0
        assert crsf.validate("150%") == 150.0
        with pytest.raises(Invalid):
            crsf.validate("auto")
        with pytest.raises(Invalid):
            crsf.validate("nana")
        with pytest.raises(Invalid):
            crsf.validate("%80")
        with pytest.raises(Invalid):
            crsf.validate("8%0%")
        with pytest.raises(Invalid):
            crsf.validate("infinity")
        with pytest.raises(Invalid):
            crsf.validate("nan")


class TestPatternTypeDetermination(BaseTestCase):
    def test_determine_path_pattern_type(self):
        assert determine_path_pattern_type("path/to/folder") == "path_prefix"
        assert determine_path_pattern_type("path/*/folder") == "glob"
        assert determine_path_pattern_type("path/**/folder") == "glob"
        assert determine_path_pattern_type("path/.*/folder") == "regex"
        assert determine_path_pattern_type("path/[a-z]*/folder") == "regex"
        assert determine_path_pattern_type("*/[a-z]*/folder") == "glob"
        assert determine_path_pattern_type("before/test-*::after/") == "glob"


class TestPreprocess(BaseTestCase):
    def test_preprocess_empty(self):
        user_input = {}
        expected_result = {}
        pre_process_yaml(user_input)
        assert expected_result == user_input

    def test_preprocess_none_in_fields(self):
        user_input = {"codecov": None}
        expected_result = {"codecov": None}
        pre_process_yaml(user_input)
        assert expected_result == user_input


class TestGlobToRegexTranslation(BaseTestCase):
    def test_translate_glob_to_regex(self):
        assert re.compile(translate_glob_to_regex("a")).match("a") is not None
        assert re.compile(translate_glob_to_regex("[abc]*")).match("a") is not None
        assert re.compile(translate_glob_to_regex("[abc]*")).match("ab") is not None
        assert re.compile(translate_glob_to_regex("[abc]")).match("d") is None
        assert re.compile(translate_glob_to_regex("[a-c]")).match("b") is not None
        assert translate_glob_to_regex("**/test*.ts") == r"(?s:.*/test[^\/]*\.ts)\Z"
        assert (
            re.compile(translate_glob_to_regex("**/test*.ts")).match("src/src2/test.ts")
            is not None
        )
        assert (
            re.compile(translate_glob_to_regex("a/*/*b*.ts")).match("a/folder/b.ts")
            is not None
        )
        assert (
            re.compile(translate_glob_to_regex("a/*/*b*.ts")).match(
                "a/folder/test_b.ts"
            )
            is not None
        )
        assert (
            re.compile(translate_glob_to_regex("a/*/*b*.ts")).match(
                "a/folder/test_b_test.ts"
            )
            is not None
        )
        assert re.compile(translate_glob_to_regex("a/*/*b*.ts")).match("a/b.ts") is None
        assert (
            re.compile(translate_glob_to_regex("a/*/*b*.ts")).match(
                "a/folder1/folder2/b.ts"
            )
            is None
        )
        assert (
            re.compile(translate_glob_to_regex("a/**/*b*.ts")).match("a/folder/b.ts")
            is not None
        )
        assert (
            re.compile(translate_glob_to_regex("a/**/*b*.ts")).match(
                "a/folder/test_b.ts"
            )
            is not None
        )
        assert (
            re.compile(translate_glob_to_regex("a/**/*b*.ts")).match(
                "a/folder/test_b_test.ts"
            )
            is not None
        )
        assert (
            re.compile(translate_glob_to_regex("a/**/*b*.ts")).match(
                "a/folder1/folder2/b.ts"
            )
            is not None
        )


class TestCustomFixPathSchemaField(BaseTestCase):
    def test_custom_fixpath(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("a::b")
        assert res == "^a::b"

    def test_custom_fixpath_removal(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("a/::")
        assert res == "a/::"

    def test_custom_fixpath_removal_no_slashes(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("a::")
        assert res == "a::"

    def test_custom_fixpath_addition(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("::b")
        assert res == "::b"

    def test_custom_fixpath_regex(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("path-*::b")
        assert res == r"(?s:path\-[^\/]*)::b"

    def test_custom_fixpath_docs_example(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("before/tests-*::after/")
        assert res == r"(?s:before/tests\-[^\/]*)::after/"

    def test_custom_fixpath_invalid_input(self):
        cfpsf = CustomFixPathSchemaField()
        # No "::" separator
        with pytest.raises(Invalid):
            cfpsf.validate("beforeafter")


class TestCoverageCommentRequirementSchemaField(object):
    @pytest.mark.parametrize(
        "input, expected",
        [
            # Old values
            pytest.param(True, [0b001]),
            pytest.param(False, [0b000]),
            # Individual values
            pytest.param("any_change", [0b001]),
            pytest.param("coverage_drop", [0b010]),
            pytest.param("uncovered_patch", [0b100]),
            # Operators
            pytest.param(
                "uncovered_patch AND uncovered_patch",
                [0b100, 0b100],
            ),
            pytest.param(
                "uncovered_patch and uncovered_patch",
                [0b100, 0b100],
            ),
            pytest.param(
                "uncovered_patch OR uncovered_patch",
                [0b100],
            ),
            pytest.param(
                "uncovered_patch or uncovered_patch",
                [0b100],
            ),
            # Combinations
            pytest.param(
                "coverage_drop or any_change",
                [0b011],
            ),
            pytest.param(
                "coverage_drop and any_change",
                [0b010, 0b001],
            ),
            pytest.param(
                "coverage_drop or uncovered_patch",
                [0b110],
            ),
            pytest.param(
                "any_change and uncovered_patch",
                [0b001, 0b100],
            ),
            pytest.param(
                "any_change and coverage_drop",
                [0b001, 0b010],
            ),
            pytest.param(
                "any_change or coverage_drop or uncovered_patch",
                [0b111],
            ),
            pytest.param(
                "any_change or coverage_drop and uncovered_patch",
                [0b011, 0b100],
            ),
            pytest.param(
                "any_change and coverage_drop and uncovered_patch",
                [0b001, 0b010, 0b100],
            ),
            pytest.param(
                "any_change and coverage_drop or uncovered_patch",
                [0b001, 0b110],
            ),
        ],
    )
    def test_coverage_comment_requirement_coercion_success(self, input, expected):
        validator = CoverageCommentRequirementSchemaField()
        assert validator.validate(input) == expected

    @pytest.mark.parametrize(
        "input, exception_message",
        [
            pytest.param(
                None, "Only bool and str are accepted values", id="invalid_input_None"
            ),
            pytest.param(
                42, "Only bool and str are accepted values", id="invalid_input_int"
            ),
            pytest.param(
                ["coverage_drop"],
                "Only bool and str are accepted values",
                id="invalid_input_list",
            ),
            pytest.param(
                "coverage_drop+any_change",
                "Failed to parse required_changes",
                id="invalid_string_no_spaces",
            ),
            pytest.param(
                "coverage_drop + any_change",
                "Failed to parse required_changes",
                id="invalid_operation",
            ),
            pytest.param("", "required_changes is empty", id="empty_string"),
            pytest.param(
                "coverage_drop any_change",
                "Failed to parse required_changes",
                id="no_operation",
            ),
            pytest.param(
                "coverage_drop AND AND any_change",
                "Failed to parse required_changes",
                id="too_many_operations",
            ),
            pytest.param(
                "coverage_drop AND any_change AND",
                "Failed to parse required_changes",
                id="incomplete_operation",
            ),
            pytest.param(
                "coverage_dropANDany_change",
                "Failed to parse required_changes",
                id="no_spaces",
            ),
            pytest.param(
                "coverage_drop AND OR any_change",
                "Failed to parse required_changes",
                id="missing_middle_operand",
            ),
            pytest.param(
                "AND",
                "Failed to parse required_changes",
                id="single_operation_no_operands",
            ),
            pytest.param(
                "AND OR AND",
                "Failed to parse required_changes",
                id="only_operations_no_operands",
            ),
        ],
    )
    def test_coverage_comment_requirement_coercion_fail(self, input, exception_message):
        validator = CoverageCommentRequirementSchemaField()
        with pytest.raises(Invalid) as exp:
            validator.validate(input)
        assert exp.value.error_message == exception_message


class TestByteSizeSchemaField(object):
    @pytest.mark.parametrize(
        "input, expected",
        [
            (100, 100),
            ("100b", 100),
            ("100 mb", 100000000),
            ("12KB", 12000),
            ("1    GB", 1000000000),
            ("12bytes", 12),
            ("24b", 24),
        ],
    )
    def test_byte_size_coercion_success(self, input, expected):
        validator = ByteSizeSchemaField()
        assert validator.validate(input) == expected

    @pytest.mark.parametrize(
        "input, error_message",
        [
            pytest.param(
                None, "Value should be int or str. Received NoneType", id="None_input"
            ),
            pytest.param(
                [], "Value should be int or str. Received list", id="list_input"
            ),
            pytest.param(
                12.34, "Value should be int or str. Received float", id="float_input"
            ),
            pytest.param(
                "200",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="no_extension",
            ),
            pytest.param(
                "kb",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="no_number",
            ),
            pytest.param(
                "100kb 100mb",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="multiple_values",
            ),
            pytest.param(
                "200.45mb",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="float_value_in_str",
            ),
            pytest.param(
                "200tb",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="invalid_extension",
            ),
            pytest.param(
                -200,
                "Only positive values accepted",
                id="negative_number",
            ),
            pytest.param(
                "-200kb",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="negative_number_with_extension",
            ),
        ],
    )
    def test_byte_size_coercion_fail(self, input, error_message):
        validator = ByteSizeSchemaField()
        with pytest.raises(Invalid) as exp:
            validator.validate(input)
        assert exp.value.error_message == error_message


class TestBundleSizeThresholdSchemaField(object):
    @pytest.mark.parametrize(
        "input, expected",
        [
            (100, ("absolute", 100)),
            ("100b", ("absolute", 100)),
            ("100 mb", ("absolute", 100000000)),
            ("12KB", ("absolute", 12000)),
            ("12%", ("percentage", 12.0)),
            ("65%", ("percentage", 65.0)),
            ("100%", ("percentage", 100.0)),
            ("200%", ("percentage", 200.0)),
            (5.5, ("percentage", 5.5)),
            (60, ("absolute", 60)),
            (60.0, ("percentage", 60.0)),
        ],
    )
    def test_byte_size_coercion_success(self, input, expected):
        validator = BundleSizeThresholdSchemaField()
        assert validator.validate(input) == expected

    @pytest.mark.parametrize(
        "input, error_message",
        [
            pytest.param(
                None, "Value should be int or str. Received NoneType", id="None_input"
            ),
            pytest.param(
                [], "Value should be int or str. Received list", id="list_input"
            ),
            pytest.param(
                "200",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="no_extension",
            ),
            pytest.param(
                "-200%",
                "-200% should be a number",
                id="negative_percentage",
            ),
            pytest.param(
                "kb",
                "Value doesn't match expected regex. Acceptable extensions are mb, kb, gb, b or bytes",
                id="absolute_no_number",
            ),
            pytest.param(
                "%",
                "% should be a number",
                id="percentage_no_number",
            ),
            pytest.param(
                "100mb%",
                "100mb should be a number",
                id="percentage_and_absolute",
            ),
        ],
    )
    def test_byte_size_coercion_fail(self, input, error_message):
        validator = BundleSizeThresholdSchemaField()
        with pytest.raises(Invalid) as exp:
            validator.validate(input)
        assert exp.value.error_message == error_message
