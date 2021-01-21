import logging

from copy import deepcopy
from typing import Any
from shared.config import get_config

from shared.validation.yaml import validate_yaml

log = logging.getLogger(__name__)


class UserYaml(object):
    def __init__(self, inner_dict):
        self.inner_dict = inner_dict

    @classmethod
    def from_dict(cls, input_dict):
        return cls(input_dict)

    def __getitem__(self, key):
        return self.inner_dict[key]

    def get(self, key, default=None):
        return self.inner_dict.get(key, default)

    def to_dict(self):
        return deepcopy(self.inner_dict)

    def read_yaml_field(self, *keys, _else=None) -> Any:
        log.debug("Field %s requested", keys)
        yaml_dict = self.inner_dict
        try:
            for key in keys:
                yaml_dict = yaml_dict[key]
            return yaml_dict
        except (AttributeError, KeyError):
            return _else

    def flag_has_carryfoward(self, flag_name):
        legacy_flag = self.inner_dict.get("flags", {}).get(flag_name)
        if legacy_flag:
            return legacy_flag.get("carryforward")
        flag_management = self.inner_dict.get("flag_management", {})
        for flag_info in flag_management.get("individual_flags", []):
            if flag_info["name"] == flag_name:
                if flag_info.get("carryforward") is not None:
                    return flag_info.get("carryforward")
        return flag_management.get("default_rules", {}).get("carryforward", False)

    def has_any_carryforward(self):
        all_flags = self.inner_dict.get("flags")
        if all_flags:
            for flag_name, flag_info in all_flags.items():
                if flag_info.get("carryforward"):
                    return True
        flag_management = self.inner_dict.get("flag_management", {})
        if flag_management.get("default_rules", {}).get("carryforward"):
            return True
        for flag_info in flag_management.get("individual_flags", []):
            if flag_info.get("carryforward"):
                return True
        return False

    def get_flag_configuration(self, flag_name):
        old_dict = self.inner_dict.get("flags", {})
        if flag_name in old_dict:
            return old_dict[flag_name]
        flag_management_dict = self.inner_dict.get("flag_management")
        if flag_management_dict is None:
            return None
        general_dict = flag_management_dict.get("default_rules", {})
        individual_flags = flag_management_dict.get("individual_flags", [])
        for f_dict in individual_flags:
            if f_dict["name"] == flag_name:
                res = deepcopy(general_dict)
                res.update(f_dict)
                return res
        return deepcopy(general_dict)

    def __eq__(self, other):
        if not isinstance(other, UserYaml):
            return False
        return self.to_dict() == other.to_dict()

    def __str__(self):
        return f"UserYaml<{self.inner_dict}>"

    @classmethod
    def get_final_yaml(cls, *, owner_yaml, repo_yaml, commit_yaml=None):
        """Given a owner yaml, repo yaml and user yaml, determines what yaml we need to use

        The answer is usually a "deep merge" between the site-level yaml, the
            owner yaml (which is set by them at the UI) and either one of commit_yaml or repo_yaml

        Why does repo_yaml gets overriden by commit_yaml, but owner_yaml doesn't?
            The idea is that the commit yaml is something at the repo level, which
                at sometime will be used to replace the current repo yaml.
            In fact, if that commit gets merged on master, then the old repo_yaml won't have any effect
                anymore. So this guarantees that if you set  yaml at a certain branch, when you merge
                that branch into master the yaml will continue to have the same effect.
            It would be a sucky behavior if your commit changes were you trying to get rid of a
                repo level yaml config and we were still merging them.

        Args:
            owner_yaml (nullable dict): The yaml that is on the owner level (ie at the owner table)
            repo_yaml (nullable dict): [description]
            commit_yaml (nullable dict): [description] (default: {None})

        Returns:
            dict - The dict we are supposed to use when concerning that user/commit
        """
        resulting_yaml = validate_yaml(
            get_config("site", default={}), show_secrets=True
        )
        if owner_yaml is not None:
            resulting_yaml = merge_yamls(resulting_yaml, owner_yaml)
        if commit_yaml is not None:
            return cls(merge_yamls(resulting_yaml, commit_yaml))
        if repo_yaml is not None:
            return cls(merge_yamls(resulting_yaml, repo_yaml))
        return cls(resulting_yaml)


def merge_yamls(d1, d2):
    if not isinstance(d1, dict) or not isinstance(d2, dict):
        return deepcopy(d2)
    res = deepcopy(d1)
    res.update(dict([(k, merge_yamls(d1.get(k, {}), v)) for k, v in d2.items()]))
    return res
