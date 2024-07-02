import datetime

from freezegun import freeze_time

from shared.components import Component
from shared.config import (
    LEGACY_DEFAULT_SITE_CONFIG,
    PATCH_CENTRIC_DEFAULT_CONFIG,
    PATCH_CENTRIC_DEFAULT_TIME_START,
)
from shared.yaml import UserYaml, merge_yamls
from shared.yaml.user_yaml import (
    OwnerContext,
    _fix_yaml_defaults_based_on_owner_onboarding_date,
    _get_possible_additional_user_yaml,
)


class TestYamlMerge(object):
    def test_merge_yamls(self):
        d1 = {
            "key_one": "value",
            "key_two": {"sub": "p"},
            "key_three": "super",
            "key_four": "pro",
        }
        d2 = {"key_two": "textnow", "key_three": "super", "key_four": "mega"}
        first_expected_result = {
            "key_four": "mega",
            "key_one": "value",
            "key_three": "super",
            "key_two": "textnow",
        }
        assert first_expected_result == merge_yamls(d1, d2)
        second_expected_result = {
            "key_four": "pro",
            "key_one": "value",
            "key_three": "super",
            "key_two": {"sub": "p"},
        }
        assert second_expected_result == merge_yamls(d2, d1)


class TestUserYaml(object):
    def test_init(self):
        d = {"value": "sample"}
        v = UserYaml(d)
        assert v is not None
        assert v["value"] == "sample"
        assert str(v) == "UserYaml<{'value': 'sample'}>"

    def test_from_dict_to_dict(self):
        d = {"value": "sample"}
        v = UserYaml.from_dict(d)
        assert v is not None
        assert v["value"] == "sample"
        assert v.get("value") == "sample"
        assert v.get("notthere") is None
        assert v.get("hshshshsh", "p") == "p"
        dicted = v.to_dict()
        assert dicted == d
        assert dicted is not d
        dicted["l"] = "banana"
        assert d == {"value": "sample"}
        assert dicted == {"value": "sample", "l": "banana"}

    def test_eq(self):
        d1 = {
            "key_one": "value",
            "key_two": {"sub": "p"},
            "key_three": "super",
            "key_four": "pro",
        }
        d2 = {"key_two": "textnow", "key_three": "super", "key_four": "mega"}
        assert UserYaml(d1) == UserYaml(d1)
        assert UserYaml(d1) != UserYaml(d2)
        assert UserYaml(d1) != d1

    def test_read_yaml_field(self):
        my_dict = {
            "key_one": "value",
            "key_two": {"sub": "p"},
            "key_three": "super",
            "key_four": "pro",
        }
        subject = UserYaml(my_dict)
        assert subject.read_yaml_field("key_two", "sub") == "p"
        assert subject.read_yaml_field("key_two", "kowabunga", _else=23) == 23

    def test_has_any_carryforward(self):
        assert UserYaml(
            {"flags": {"banana": {"carryforward": True}}, "flag_management": {}}
        ).has_any_carryforward()
        assert not UserYaml(
            {"flags": {"banana": {"carryforward": False}}, "flag_management": {}}
        ).has_any_carryforward()
        assert UserYaml(
            {
                "flags": {"banana": {"carryforward": False}},
                "flag_management": {"default_rules": {"carryforward": True}},
            }
        ).has_any_carryforward()
        assert UserYaml(
            {
                "flags": {"banana": {"carryforward": False}},
                "flag_management": {
                    "default_rules": {"carryforward": False},
                    "individual_flags": [{"name": "strawberry", "carryforward": True}],
                },
            }
        ).has_any_carryforward()

    def test_flag_has_carryfoward(self):
        assert UserYaml(
            {"flags": {"banana": {"carryforward": True}}, "flag_management": {}}
        ).flag_has_carryfoward("banana")
        assert not UserYaml(
            {"flags": {"banana": {"carryforward": False}}, "flag_management": {}}
        ).flag_has_carryfoward("banana")
        subject = UserYaml(
            {
                "flags": {"banana": {"carryforward": False}},
                "flag_management": {"default_rules": {"carryforward": True}},
            }
        )
        assert not subject.flag_has_carryfoward("banana")
        assert subject.flag_has_carryfoward("strawberry")
        subject_2 = UserYaml(
            {
                "flags": {"banana": {"carryforward": False}},
                "flag_management": {
                    "default_rules": {"carryforward": False},
                    "individual_flags": [{"name": "strawberry", "carryforward": True}],
                },
            }
        )
        assert not subject_2.flag_has_carryfoward("banana")
        assert subject_2.flag_has_carryfoward("strawberry")
        assert not subject_2.flag_has_carryfoward("pineapple")

    def test_get_flag_configuration(self):
        old_style = UserYaml({"flags": {"banana": {"key_one": True}}})
        assert old_style.get_flag_configuration("banana") == {"key_one": True}
        assert old_style.get_flag_configuration("pineapple") is None
        assert UserYaml(
            {"flags": {"banana": {"key_one": True}}, "flag_management": {}}
        ).get_flag_configuration("banana") == {"key_one": True}
        assert UserYaml(
            {
                "flag_management": {
                    "default_rules": {"key_one": False, "key_two": "something"}
                }
            }
        ).get_flag_configuration("banana") == {"key_one": False, "key_two": "something"}
        subject = UserYaml(
            {
                "flags": {"banana": {"carryforward": False}},
                "flag_management": {
                    "default_rules": {"key_one": False, "key_two": "something"}
                },
            }
        )
        assert subject.get_flag_configuration("banana") == {"carryforward": False}
        assert subject.get_flag_configuration("strawberry") == {
            "key_one": False,
            "key_two": "something",
        }
        subject_2 = UserYaml(
            {
                "flags": {"banana": {"carryforward": False}},
                "flag_management": {
                    "default_rules": {"key_one": False, "key_two": "something"},
                    "individual_flags": [
                        {
                            "name": "strawberry",
                            "key_one": True,
                            "key_three": ["array", "values"],
                        }
                    ],
                },
            }
        )
        assert subject_2.get_flag_configuration("banana") == {"carryforward": False}
        assert subject_2.get_flag_configuration("strawberry") == {
            "key_one": True,
            "key_three": ["array", "values"],
            "key_two": "something",
            "name": "strawberry",
        }
        assert subject_2.get_flag_configuration("pineapple") == {
            "key_one": False,
            "key_two": "something",
        }

    def test_get_final_yaml(self, mock_configuration):
        mock_configuration._params["site"] = {"codecov": {"max_report_age": 86400}}
        owner_yaml = {"key": {"value": "one", "a": "b"}}
        repo_yaml = {"barber": "shop"}
        commit_yaml = {"key": {"value": "two", "c": "d"}}
        expected_result = {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
        }
        assert (
            UserYaml.get_final_yaml(
                owner_yaml=owner_yaml, repo_yaml=repo_yaml, commit_yaml=commit_yaml
            ).to_dict()
            == expected_result
        )

    def test_get_final_yaml_with_additional_user_yaml(self, mock_configuration):
        mock_configuration._params["site"] = {"codecov": {"max_report_age": 86400}}
        mock_configuration._params["additional_user_yamls"] = [
            {"percentage": 10, "name": "banana", "override": {"a": 2, "b": 3}},
            {"percentage": 30, "name": "apple", "override": {"d": "klmnop", "b": 3}},
        ]
        owner_yaml = {"key": {"value": "one", "a": "b"}}
        repo_yaml = {"barber": "shop"}
        commit_yaml = {"key": {"value": "two", "c": "d"}}
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml, repo_yaml=repo_yaml, commit_yaml=commit_yaml
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
        }
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml,
            repo_yaml=repo_yaml,
            commit_yaml=commit_yaml,
            ownerid=100,
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
            "a": 2,
            "b": 3,
        }
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml,
            repo_yaml=repo_yaml,
            commit_yaml=commit_yaml,
            ownerid=121,
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
            "b": 3,
            "d": "klmnop",
        }
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml,
            repo_yaml=repo_yaml,
            commit_yaml=commit_yaml,
            ownerid=140,
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
        }

    def test_get_final_yaml_with_additional_user_yaml_via_ownercontext(
        self, mock_configuration
    ):
        mock_configuration._params["site"] = {"codecov": {"max_report_age": 86400}}
        mock_configuration._params["additional_user_yamls"] = [
            {"percentage": 10, "name": "banana", "override": {"a": 2, "b": 3}},
            {"percentage": 30, "name": "apple", "override": {"d": "klmnop", "b": 3}},
        ]
        owner_yaml = {"key": {"value": "one", "a": "b"}}
        repo_yaml = {"barber": "shop"}
        commit_yaml = {"key": {"value": "two", "c": "d"}}
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml, repo_yaml=repo_yaml, commit_yaml=commit_yaml
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
        }
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml,
            repo_yaml=repo_yaml,
            commit_yaml=commit_yaml,
            owner_context=OwnerContext(ownerid=100),
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
            "a": 2,
            "b": 3,
        }
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml,
            repo_yaml=repo_yaml,
            commit_yaml=commit_yaml,
            owner_context=OwnerContext(ownerid=121),
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
            "b": 3,
            "d": "klmnop",
        }
        assert UserYaml.get_final_yaml(
            owner_yaml=owner_yaml,
            repo_yaml=repo_yaml,
            commit_yaml=commit_yaml,
            owner_context=OwnerContext(ownerid=140),
        ).to_dict() == {
            "codecov": {"max_report_age": 86400},
            "key": {"a": "b", "c": "d", "value": "two"},
        }

    def test_get_final_yaml_no_commit_yaml(self, mock_configuration):
        mock_configuration._params["site"] = {"codecov": {"max_report_age": 86400}}
        owner_yaml = {"key": {"value": "one", "a": "b"}}
        repo_yaml = {"barber": "shop"}
        expected_result = {
            "key": {"a": "b", "value": "one"},
            "barber": "shop",
            "codecov": {"max_report_age": 86400},
        }
        assert (
            UserYaml.get_final_yaml(
                owner_yaml=owner_yaml, repo_yaml=repo_yaml, commit_yaml=None
            ).to_dict()
            == expected_result
        )

    def test_get_final_yaml_only_owner_yaml(self, mock_configuration):
        mock_configuration._params["site"] = {"codecov": {"max_report_age": 86400}}
        owner_yaml = {"key": {"value": "one", "a": "b"}}
        expected_result = {
            "key": {"a": "b", "value": "one"},
            "codecov": {"max_report_age": 86400},
        }
        assert (
            UserYaml.get_final_yaml(
                owner_yaml=owner_yaml, repo_yaml=None, commit_yaml=None
            ).to_dict()
            == expected_result
        )

    def test_get_final_yaml_nothing(self, mock_configuration):
        mock_configuration._params["site"] = {"codecov": {"max_report_age": 86400}}
        expected_result = {"codecov": {"max_report_age": 86400}}
        assert (
            UserYaml.get_final_yaml(
                owner_yaml=None, repo_yaml=None, commit_yaml=None
            ).to_dict()
            == expected_result
        )

    @freeze_time("2024-04-30 00:00:00.000")
    def test_default_yaml_behavior_change(self):
        current_yaml = LEGACY_DEFAULT_SITE_CONFIG
        day_timedelta = datetime.timedelta(days=1)
        patch_centric_expected_onboarding_date = (
            datetime.datetime.now(datetime.timezone.utc) + day_timedelta
        )
        no_change_expected_onboarding_date = (
            datetime.datetime.now(datetime.timezone.utc) - day_timedelta
        )
        no_change = _fix_yaml_defaults_based_on_owner_onboarding_date(
            current_yaml, no_change_expected_onboarding_date
        )
        assert no_change == current_yaml
        patch_centric = _fix_yaml_defaults_based_on_owner_onboarding_date(
            current_yaml, patch_centric_expected_onboarding_date
        )
        assert patch_centric != current_yaml
        assert patch_centric == PATCH_CENTRIC_DEFAULT_CONFIG

    def test_get_final_yaml_default_based_on_owner_context(self):
        day_timedelta = datetime.timedelta(days=1)
        patch_centric_expected_onboarding_date = (
            PATCH_CENTRIC_DEFAULT_TIME_START + day_timedelta
        )
        no_change_expected_onboarding_date = (
            PATCH_CENTRIC_DEFAULT_TIME_START - day_timedelta
        )
        legacy_default = UserYaml.get_final_yaml(
            owner_yaml=None,
            repo_yaml=None,
            commit_yaml=None,
            owner_context=OwnerContext(
                owner_onboarding_date=no_change_expected_onboarding_date
            ),
        )
        assert legacy_default.to_dict() == {
            "codecov": {"require_ci_to_pass": True, "notify": {"wait_for_ci": True}},
            "coverage": {
                "precision": 2,
                "round": "down",
                "range": [60.0, 80.0],
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
        patch_centric_default = UserYaml.get_final_yaml(
            owner_yaml=None,
            repo_yaml=None,
            commit_yaml=None,
            owner_context=OwnerContext(
                owner_onboarding_date=patch_centric_expected_onboarding_date
            ),
        )
        assert patch_centric_default.to_dict() == {
            "codecov": {"require_ci_to_pass": True, "notify": {"wait_for_ci": True}},
            "coverage": {
                "precision": 2,
                "round": "down",
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
                "behavior": "default",
                "show_carryforward_flags": False,
                "hide_project_coverage": True,
            },
            "slack_app": True,
            "github_checks": {"annotations": True},
        }

    def test_get_possible_additional_user_yaml_empty(self, mock_configuration):
        assert _get_possible_additional_user_yaml(1) == {}
        assert _get_possible_additional_user_yaml(101) == {}

    def test_get_possible_additional_user_yaml(self, mock_configuration):
        mock_configuration._params["additional_user_yamls"] = [
            {"percentage": 10, "name": "banana", "override": {"a": 2, "b": 3}},
            {"percentage": 30, "name": "apple", "override": {"d": "kllmnop", "b": 3}},
        ]
        assert _get_possible_additional_user_yaml(0) == {"a": 2, "b": 3}
        assert _get_possible_additional_user_yaml(1) == {"a": 2, "b": 3}
        assert _get_possible_additional_user_yaml(9) == {"a": 2, "b": 3}
        assert _get_possible_additional_user_yaml(10) == {"d": "kllmnop", "b": 3}
        assert _get_possible_additional_user_yaml(11) == {"d": "kllmnop", "b": 3}
        assert _get_possible_additional_user_yaml(39) == {"d": "kllmnop", "b": 3}
        assert _get_possible_additional_user_yaml(40) == {}
        assert _get_possible_additional_user_yaml(41) == {}
        assert _get_possible_additional_user_yaml(100) == {"a": 2, "b": 3}
        assert _get_possible_additional_user_yaml(101) == {"a": 2, "b": 3}

    def test_get_components_no_default(self):
        user_yaml = UserYaml(
            {
                "component_management": {
                    "individual_components": [
                        {"component_id": "py_files", "paths": [r".*\.py"]}
                    ]
                }
            }
        )
        components = user_yaml.get_components()
        assert len(components) == 1
        assert components == [
            Component(
                component_id="py_files",
                paths=[r".*\.py"],
                name="",
                flag_regexes=[],
                statuses=[],
            )
        ]

    def test_get_components_default_no_components(self):
        user_yaml = UserYaml({"component_management": {}})
        components = user_yaml.get_components()
        assert len(components) == 0

    def test_get_components_default_only(self):
        user_yaml = UserYaml(
            {
                "component_management": {
                    "default_rules": {"paths": [r".*\.py"], "flag_regexes": [r"flag.*"]}
                }
            }
        )
        components = user_yaml.get_components()
        assert len(components) == 0

    def test_get_components_all(self):
        user_yaml = UserYaml(
            {
                "component_management": {
                    "default_rules": {
                        "paths": [r".*\.py"],
                        "flag_regexes": [r"flag.*"],
                    },
                    "individual_components": [
                        {"component_id": "go_files", "paths": [r".*\.go"]},
                        {"component_id": "rules_from_default"},
                        {
                            "component_id": "I have my flags",
                            "flag_regexes": [r"python-.*"],
                        },
                        {
                            "component_id": "required",
                            "name": "display",
                            "flag_regexes": [],
                            "paths": [r"src/.*"],
                        },
                    ],
                }
            }
        )
        components = user_yaml.get_components()
        assert len(components) == 4
        assert components == [
            Component(
                component_id="go_files",
                paths=[r".*\.go"],
                name="",
                flag_regexes=[r"flag.*"],
                statuses=[],
            ),
            Component(
                component_id="rules_from_default",
                paths=[r".*\.py"],
                name="",
                flag_regexes=[r"flag.*"],
                statuses=[],
            ),
            Component(
                component_id="I have my flags",
                paths=[r".*\.py"],
                name="",
                flag_regexes=[r"python-.*"],
                statuses=[],
            ),
            Component(
                component_id="required",
                name="display",
                paths=[r"src/.*"],
                flag_regexes=[],
                statuses=[],
            ),
        ]
