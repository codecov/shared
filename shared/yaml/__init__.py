"""
Package for user yaml things

This package depends on:

- shared.config
- shared.validation

And therefore should not be imported by those
"""

from copy import deepcopy

from .fetcher import (
    determine_commit_yaml_location,
    fetch_current_yaml_from_provider_via_reference,
)
from .user_yaml import UserYaml, merge_yamls

__all__ = [
    "deepcopy",
    "determine_commit_yaml_location",
    "fetch_current_yaml_from_provider_via_reference",
    "UserYaml",
    "merge_yamls",
]
