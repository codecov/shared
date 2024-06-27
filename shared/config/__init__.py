import collections
import json
import logging
import os
import re
from base64 import b64decode
from copy import deepcopy
from datetime import datetime
from typing import Any, List, Tuple

from yaml import safe_load as yaml_load

from shared.validation.install import validate_install_configuration


class MissingConfigException(Exception):
    pass


log = logging.getLogger(__name__)

LEGACY_DEFAULT_SITE_CONFIG = {
    "codecov": {"require_ci_to_pass": True},
    "coverage": {
        "precision": 2,
        "round": "down",
        "range": "60...80",
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
    "slack_app": True,
    "github_checks": {"annotations": True},
}

PATCH_CENTRIC_DEFAULT_TIME_START = datetime.fromisoformat(
    "2024-04-30 00:00:00.000+00:00"
)

PATCH_CENTRIC_DEFAULT_CONFIG = {
    **LEGACY_DEFAULT_SITE_CONFIG,
    "coverage": {
        "precision": 2,
        "round": "down",
        # The range is created with the transformed version (in the legacy it's transformed by validation)
        # Because this bit of dict will not be validated.
        "range": [60.0, 80.0],
        "status": {
            "project": False,
            "patch": True,
            "changes": False,
            "default_rules": {"flag_coverage_not_uploaded_behavior": "include"},
        },
    },
    "comment": {
        "layout": "condensed_header, flags, tree, component",
        "hide_project_coverage": True,
        "behavior": "default",
        "show_carryforward_flags": False,
    },
}

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
        "database_url": "postgresql://postgres:@postgres:5432/postgres",
    },
    "site": LEGACY_DEFAULT_SITE_CONFIG,
    "setup": {
        "timeseries": {"enabled": False},
    },
}


def update(d, u):
    d = deepcopy(d)
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping) and isinstance(
            d.get(k), collections.abc.Mapping
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
            if not env_var.startswith("__") and "__" in env_var:
                multiple_level_vars, data = self._parse_path_and_value_from_envvar(
                    env_var
                )
                current = val
                for c in multiple_level_vars[:-1]:
                    current = current.setdefault(c.lower(), {})
                current[multiple_level_vars[-1].lower()] = data
        return val

    def _env_var_value_cast(self, data):
        if isinstance(data, str):
            if data in ("true", "True", "TRUE", "on", "On", "ON"):
                return True
            elif data in ("false", "False", "FALSE", "off", "Off", "OFF"):
                return False
            elif re.match(r"^-?\d+$", data):
                return int(data)
            elif re.match(r"^-?\d+\.\d+$", data):
                try:
                    return float(data)
                except ValueError:
                    pass

        return data

    def _parse_path_and_value_from_envvar(
        self, env_var_name: str
    ) -> Tuple[List[str], Any]:
        """
        Given an envvar, calculate both the data that needs to be put in the config and
            the location in the config where it needs to be set.

        For example:
            ONE__TWO__THREE='value' --> { 'one': { 'two': { 'three': 'value' }}}

        Args:
            env_var_name (str): The envvar we want to load data from

        Returns:
            Tuple[List[str], Any]: Two elements:
                - The path where the data needs to be set
                - The actual data
        """
        # Split env variables on "__" to get values for nested config fields
        should_load_from_json = env_var_name.startswith("JSONCONFIG___")
        path_to_use = env_var_name if not should_load_from_json else env_var_name[13:]
        data = os.getenv(env_var_name)
        data = data if not should_load_from_json else json.loads(data)
        data = self._env_var_value_cast(data)
        return (path_to_use.split("__"), data)

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
            unvalidated_final_result = update(temp_result, env_vars)
            final_result = validate_install_configuration(unvalidated_final_result)
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
                    "Unable to read file specified in config",
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
