from copy import deepcopy

from .user_yaml import UserYaml


def merge_yamls(d1, d2):
    if not isinstance(d1, dict) or not isinstance(d2, dict):
        return deepcopy(d2)
    res = deepcopy(d1)
    res.update(dict([(k, merge_yamls(d1.get(k, {}), v)) for k, v in d2.items()]))
    return res
