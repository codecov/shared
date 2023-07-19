import re

import pytest

from shared.validation.helpers import (
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
        assert compiled.match("a/path/b/file_2.py") is not None
        assert compiled.match("a/path/b/more_path/some_file.py") is not None
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
        assert compiled.match("a/path/b/some_file.py") is not None
        assert compiled.match("a/path/b/more_path/some_file.py") is not None
        assert compiled.match("a/path/path2/b") is not None
        assert compiled.match("a/path/path2/b/some_file.py") is not None
        assert compiled.match("a/path/path2/b/more_path/some_file.py") is not None
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
        assert translate_glob_to_regex("**/test*.ts") == "(?s:.*/test[^\/]*\.ts)\Z"
        assert (
            re.compile(translate_glob_to_regex("**/test*.ts")).match("src/src2/test.ts")
            is not None
        )
        print(f'"a/*/*b*.ts" => {translate_glob_to_regex("a/*/*b*.ts")}')
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
        print(f'"a/**/*b*.ts" => {translate_glob_to_regex("a/**/*b*.ts")}')
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
