from shared.config import get_config, load_file_from_path_at_config
from shared.utils.test_utils import mock_config_helper


class TestMockConfigHelper(object):
    def test_mock_config_helper_get(self, mocker):
        mock_config_helper(mocker, configs={"foo.bar": "baz"})
        assert get_config("foo", "bar", default="not baz") == "baz"

    def test_mock_config_helper_load_file(self, mocker):
        mock_config_helper(mocker, file_configs={"foo.bar": "baz"})
        assert load_file_from_path_at_config("foo", "bar") == "baz"
