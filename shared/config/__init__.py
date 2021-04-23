import os
import logging
from copy import deepcopy

from yaml import safe_load as yaml_load
from base64 import b64decode
import collections


class MissingConfigException(Exception):
    pass


log = logging.getLogger(__name__)

default_config = {
    "services": {
        "minio": {
            "host": "minio",
            "access_key_id": "codecov-default-key",
            "secret_access_key": "codecov-default-secret",
            "verify_ssl": False,
            "iam_auth": False,
            "iam_endpoint": None,
            "hash_key": "ab164bf3f7d947f2a0681b215404873e",
        },
    },
    "site": {
        "codecov": {"require_ci_to_pass": True},
        "coverage": {
            "precision": 2,
            "round": "down",
            "range": "70...100",
            "status": {
                "project": True,
                "patch": True,
                "changes": False,
                "default_rules": {"flag_coverage_not_uploaded_behavior": "include"},
            },
        },
        "comment": {
            "layout": "reach,diff,flags,tree,reach",
            "behavior": "default",
            "show_carryforward_flags": False,
        },
        "github_checks": {"annotations": True},
    },
    "setup": {"segment": {"enabled": False, "key": "test93utbz4l7nybyx5y960y8pb8w672"}},
}


def update(d, u):
    d = deepcopy(d)
    for k, v in u.items():
        if isinstance(v, collections.Mapping) and isinstance(
            d.get(k), collections.Mapping
        ):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


class ConfigHelper(object):
    def __init__(self):
        self._params = None
        self.loaded_files = {}

    # Load config values from environment variables
    def load_env_var(self):
        val = {}
        for env_var in os.environ:
            if not env_var.startswith("__"):
                # Split env variables on "__" to get values for nested config fields
                # For example: ONE__TWO__THREE='value' --> { 'one': { 'two': { 'three': 'value' }}}
                multiple_level_vars = env_var.split("__")
                if len(multiple_level_vars) > 1:
                    current = val
                    for c in multiple_level_vars[:-1]:
                        current = current.setdefault(c.lower(), {})
                    current[multiple_level_vars[-1].lower()] = os.getenv(env_var)
        return val

    @property
    def params(self):
        """
            Construct the config by combining default values, yaml config, and env vars.
            An env var overrides a yaml config value, which overrides the default values.
        """
        if self._params is None:
            content = self.yaml_content()
            env_vars = self.load_env_var()
            temp_result = update(default_config, content)
            final_result = update(temp_result, env_vars)
            self.set_params(final_result)
        return self._params

    def set_params(self, val):
        self._params = val

    def get(self, *args, **kwargs):
        current_p = self.params
        for el in args:
            try:
                current_p = current_p[el]
            except (KeyError, TypeError):
                raise MissingConfigException(args)
        return current_p

    def load_yaml_file(self):
        yaml_path = os.getenv("CODECOV_YML", "/config/codecov.yml")
        with open(yaml_path, "r") as c:
            return c.read()

    def yaml_content(self):
        try:
            return yaml_load(self.load_yaml_file())
        except FileNotFoundError:
            return {}

    def load_filename_from_path(self, *args):
        if args not in self.loaded_files:
            location = self.get(*args)
            if isinstance(location, dict):
                if location.get("source_type") == "base64env":
                    self.loaded_files[args] = b64decode(location.get("value")).decode()
                    return self.loaded_files[args]
                else:
                    assert location.get("source_type") == "filepath"
                    location = location.get("value")
            try:
                with open(location, "r") as _file:
                    self.loaded_files[args] = _file.read()
            except FileNotFoundError:
                log.exception(
                    "Unable to read filepath for install YAML",
                    extra=dict(file_location=location, path_args=list(args)),
                )
                raise
        return self.loaded_files[args]


config_class_instance = ConfigHelper()


def _get_config_instance():
    return config_class_instance


def get_config(*path, default=None):
    config = _get_config_instance()
    try:
        return config.get(*path)
    except MissingConfigException:
        return default


def load_file_from_path_at_config(*args):
    config = _get_config_instance()
    return config.load_filename_from_path(*args)


def get_verify_ssl(service):
    verify = get_config(service, "verify_ssl")
    if verify is False:
        return False
    return get_config(service, "ssl_pem") or os.getenv("REQUESTS_CA_BUNDLE")
