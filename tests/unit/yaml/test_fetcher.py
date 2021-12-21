import mock
import pytest

from shared.torngit.exceptions import TorngitObjectNotFoundError
from shared.yaml import (
    determine_commit_yaml_location,
    fetch_current_yaml_from_provider_via_reference,
)

sample_yaml = """
codecov:
  notify:
    require_ci_to_pass: yes
"""

commitid = "e1ade"


class TestYamlSavingService(object):
    @pytest.mark.asyncio
    async def test_determine_commit_yaml_location(self, mocker):
        mocked_result = [
            {"name": ".gitignore", "path": ".gitignore", "type": "file"},
            {"name": ".travis.yml", "path": ".travis.yml", "type": "file"},
            {"name": "README.rst", "path": "README.rst", "type": "file"},
            {"name": "awesome", "path": "awesome", "type": "folder"},
            {"name": "codecov", "path": "codecov", "type": "file"},
            {"name": "codecov.yaml", "path": "codecov.yaml", "type": "file"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        f = mocked_result
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=f)
        )
        res = await determine_commit_yaml_location(commitid, valid_handler)
        assert res == "codecov.yaml"

    @pytest.mark.asyncio
    async def test_determine_commit_yaml_location_no_yaml(self, mocker):
        mocked_result = [
            {"name": ".gitignore", "path": ".gitignore", "type": "file"},
            {"name": ".travis.yml", "path": ".travis.yml", "type": "file"},
            {"name": "README.rst", "path": "README.rst", "type": "file"},
            {"name": "awesome", "path": "awesome", "type": "folder"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        f = mocked_result
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=f)
        )
        res = await determine_commit_yaml_location(commitid, valid_handler)
        assert res is None

    @pytest.mark.asyncio
    async def test_determine_commit_yaml_location_no_name(self, mocker):
        mocked_result = [
            {"path": ".gitignore", "type": "file"},
            {"path": ".travis.yml", "type": "file"},
            {"path": "README.rst", "type": "file"},
            {"path": "awesome", "type": "folder"},
            {"path": "codecov", "type": "file"},
            {"path": "codecov.yaml", "type": "file"},
            {"path": "tests", "type": "folder"},
        ]
        f = mocked_result
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=f)
        )
        res = await determine_commit_yaml_location(commitid, valid_handler)
        assert res == "codecov.yaml"

    @pytest.mark.asyncio
    async def test_determine_commit_yaml_nested_folder(self, mocker):
        mocked_result = [
            {"name": ".gitignore", "path": ".gitignore", "type": "file"},
            {"name": ".travis.yml", "path": ".travis.yml", "type": "file"},
            {"name": "README.rst", "path": "README.rst", "type": "file"},
            {"name": ".github", "path": ".github", "type": "folder"},
            {"name": "codecov", "path": "codecov", "type": "file"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        files_inside_folder = [
            {"name": "code.py", "path": ".github/code.py", "type": "file"},
            {"name": "__init__.py", "path": ".github/__init__.py", "type": "file"},
            {
                "name": "anotha_folder",
                "path": ".github/anotha_folder",
                "type": "folder",
            },
            {"name": "codecov", "path": ".github/codecov", "type": "folder"},
            {"name": "codecov.yaml", "path": ".github/codecov.yaml", "type": "file"},
        ]
        f = mocked_result
        list_file_future = files_inside_folder
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=f),
            list_files=mock.AsyncMock(return_value=list_file_future),
        )
        res = await determine_commit_yaml_location(commitid, valid_handler)
        assert res == ".github/codecov.yaml"

    @pytest.mark.asyncio
    async def test_determine_commit_yaml_nested_folder_noname(self, mocker):
        mocked_result = [
            {"path": ".gitignore", "type": "file"},
            {"path": ".travis.yml", "type": "file"},
            {"path": "README.rst", "type": "file"},
            {"path": ".github", "type": "folder"},
            {"path": "codecov", "type": "file"},
            {"path": "tests", "type": "folder"},
        ]
        files_inside_folder = [
            {"path": ".github/code.py", "type": "file"},
            {"path": ".github/__init__.py", "type": "file"},
            {"path": ".github/anotha_folder", "type": "folder"},
            {"path": ".github/codecov", "type": "folder"},
            {"path": ".github/codecov.yaml", "type": "file"},
        ]
        f = mocked_result
        list_file_future = files_inside_folder
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=f),
            list_files=mock.AsyncMock(return_value=list_file_future),
        )
        res = await determine_commit_yaml_location(commitid, valid_handler)
        assert res == ".github/codecov.yaml"

    @pytest.mark.asyncio
    async def test_determine_commit_yaml_location_multiple(self, mocker):
        mocked_result = [
            {"name": "READMEs", "path": "README.rst", "type": "folder"},
            {"name": "codecov.yml", "path": "codecov.yml", "type": "file"},
            {"name": ".codecov.yml", "path": ".codecov.yml", "type": "file"},
            {"name": "codecov.yaml", "path": "codecov.yaml", "type": "file"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        f = mocked_result
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=f)
        )
        res = await determine_commit_yaml_location(commitid, valid_handler)
        assert res == "codecov.yml"

    @pytest.mark.asyncio
    async def test_fetch_commit_yaml_from_provider(self, mocker):
        mocked_list_files_result = [
            {"name": ".gitignore", "path": ".gitignore", "type": "file"},
            {"name": ".travis.yml", "path": ".travis.yml", "type": "file"},
            {"name": "README.rst", "path": "README.rst", "type": "file"},
            {"name": "awesome", "path": "awesome", "type": "folder"},
            {"name": "codecov", "path": "codecov", "type": "file"},
            {"name": "codecov.yaml", "path": "codecov.yaml", "type": "file"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        list_files_future = mocked_list_files_result
        contents_result = {"content": sample_yaml}
        contents_result_future = contents_result
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=list_files_future),
            get_source=mock.AsyncMock(return_value=contents_result_future),
        )
        res = await fetch_current_yaml_from_provider_via_reference(
            commitid, valid_handler
        )
        assert res == sample_yaml
        valid_handler.list_top_level_files.assert_called_with(commitid)
        valid_handler.get_source.assert_called_with("codecov.yaml", commitid)

    @pytest.mark.asyncio
    async def test_fetch_commit_yaml_from_no_yaml(self, mocker):
        mocked_list_files_result = []
        list_files_future = mocked_list_files_result
        contents_result = {"content": sample_yaml}
        contents_result_future = contents_result
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=list_files_future),
            get_source=mock.AsyncMock(return_value=contents_result_future),
        )
        res = await fetch_current_yaml_from_provider_via_reference(
            commitid, valid_handler
        )
        assert res == None
        valid_handler.list_top_level_files.assert_called_with(commitid)

    @pytest.mark.asyncio
    async def test_fetch_commit_yaml_from_no_yaml_on_provider(self, mocker):
        mocked_list_files_result = [
            {"name": ".gitignore", "path": ".gitignore", "type": "file"},
            {"name": ".travis.yml", "path": ".travis.yml", "type": "file"},
            {"name": "README.rst", "path": "README.rst", "type": "file"},
            {"name": "awesome", "path": "awesome", "type": "folder"},
            {"name": "codecov", "path": "codecov", "type": "file"},
            {"name": "codecov.yaml", "path": "codecov.yaml", "type": "file"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        list_files_future = mocked_list_files_result
        contents_result = {"content": sample_yaml}
        contents_result_future = contents_result
        exception_get_source = TorngitObjectNotFoundError("not found", ":(")
        valid_handler = mocker.MagicMock(
            list_top_level_files=mock.AsyncMock(return_value=list_files_future),
            get_source=mock.AsyncMock(side_effect=exception_get_source),
        )
        res = await fetch_current_yaml_from_provider_via_reference(
            commitid, valid_handler
        )
        assert res == None
        valid_handler.list_top_level_files.assert_called_with(commitid)
        valid_handler.get_source.assert_called_with("codecov.yaml", commitid)
