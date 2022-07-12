import pytest

from shared.encryption.yaml_secret import get_yaml_secret_encryptor


@pytest.mark.parametrize(
    "user_input, expected_output",
    [
        (
            "v1::uwP3wUeU5tTSjHM14F1C4X372EQo8FlLIhYMVn6E5FlUBKs2CAgJCNLXx9WYxIk8VAk6b2yiffladvs0GatPdXCaauPruGbOC7Pbp2xlLl6QkWFL0cG0K5l+4o5UpwGz",
            "github/44376991/308757874/Will no one rid me of this turbulent priest",
        ),
        ("wnb1smVbBvjHNFgEgK2RV9rfVhGygj3IAPOkWp3rO8o=", "Im a banana"),
        ("default_enc::wnb1smVbBvjHNFgEgK2RV9rfVhGygj3IAPOkWp3rO8o=", "Im a banana"),
        (
            "v2::FpVtGkoVY7ACYicwfD1QP3oAPOmJj+eM24l2IkWfiNMtVInE8JVNJnJZJqIKmVLy7LW479oJuIfFRWI2COIJrA==",
            "gitlab/1234/876/Talkthetalkwalkthewalk",
        ),
    ],
)
def test_yaml_secret_cases(user_input, expected_output, mock_configuration):
    assert get_yaml_secret_encryptor().decode(user_input) == expected_output


@pytest.mark.parametrize(
    "user_config_input, user_input, expected_output",
    [
        (
            "messymessysecretstuff",
            "v2::ZypitOrairOs1O11UpaYuD3rLldHcu5zYjKLEAGK54QmYl2IMrP4uQ/ZOoOLaBdJO333ythhPRVHTMy7xqOIxnLc+c32oVlkt5zpjD224my4RJX5bjh0JMZ3Rgbi/4db",
            "github/44376991/308757874/Will no one rid me of this turbulent priest",
        ),
        (
            "19JOdicq0fCF47Pjv9RsG20xj6MIz4DXkZA5aFK4uOY",
            "v2::+QA+DDAeWcTLqrSPmYcV6HqIUVK+U6SzBQznO7IXjdynj4UPezqcDQYOg8dd/LEy81GpeR05VmrLWScA0N8HdQndBZH9tjb2W9h+d8MpBuIJCEVuf+q7otlzwJz6L9Yo",
            "github/44376991/308757874/Will no one rid me of this turbulent priest",
        ),
        ("whatever", "wnb1smVbBvjHNFgEgK2RV9rfVhGygj3IAPOkWp3rO8o=", "Im a banana"),
        ("whenever", "wnb1smVbBvjHNFgEgK2RV9rfVhGygj3IAPOkWp3rO8o=", "Im a banana"),
    ],
)
def test_yaml_secret_cases_with_different_config(
    user_config_input, user_input, expected_output, mock_configuration
):
    mock_configuration._params["setup"]["encryption"] = {
        "yaml_secret": user_config_input
    }
    assert get_yaml_secret_encryptor().decode(user_input) == expected_output
