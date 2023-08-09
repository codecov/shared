from shared.config import ConfigHelper


def mock_config_helper(mocker, configs={}, file_configs={}):
    """
    Generic utility for mocking two functions on `ConfigHelper`:
    - `get()`, which takes a config key and returns its value
    - `load_filename_from_path()`, which takes a config key, treats its value as
      a file path, and returns the contents of the file.

    These functions underpin the non-method APIs of the config module.

    Example:
        configs = {"github.client_id": "testvalue"}
        file_configs = {"github.integration.pem": "--------BEGIN RSA PRIVATE KEY-----..."}
        mock_config_helper(mocker, configs, file_configs)

        assert "testvalue" == get_config("github", "client_id")
        assert "BEGIN RSA" in load_file_from_path_at_config("github", "integration", "pem")
    """
    orig_get = ConfigHelper.get
    orig_load_file = ConfigHelper.load_filename_from_path

    def mock_get(obj, *args, **kwargs):
        conf_key = ".".join(args)
        if conf_key in configs:
            return configs.get(conf_key)
        else:
            return orig_get(obj, *args, **kwargs)

    def mock_load_file(obj, *args, **kwargs):
        conf_key = ".".join(args)
        if conf_key in file_configs:
            return file_configs.get(conf_key)
        else:
            return orig_load_file(obj, *args, **kwargs)

    mocker.patch.object(ConfigHelper, "get", mock_get)
    mocker.patch.object(ConfigHelper, "load_filename_from_path", mock_load_file)
