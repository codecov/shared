from shared.yaml import UserYaml, merge_yamls


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
        expected_result = {
            "codecov": {"max_report_age": 86400},
        }
        assert (
            UserYaml.get_final_yaml(
                owner_yaml=None, repo_yaml=None, commit_yaml=None
            ).to_dict()
            == expected_result
        )
