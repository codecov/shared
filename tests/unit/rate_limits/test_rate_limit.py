import datetime
from unittest.mock import patch

import pytest
from mock import MagicMock
from redis import RedisError

from shared.django_apps.codecov_auth.models import (
    GITHUB_APP_INSTALLATION_DEFAULT_NAME,
    GithubAppInstallation,
)
from shared.django_apps.codecov_auth.tests.factories import OwnerFactory
from shared.django_apps.core.tests.factories import RepositoryFactory
from shared.helpers.redis import get_redis_connection
from shared.rate_limits import (
    determine_entity_redis_key,
    determine_if_entity_is_rate_limited,
    gh_app_key_name,
    set_entity_to_rate_limited,
)


@pytest.fixture
def mock_configuration(mock_configuration):
    custom_params = {
        "github": {
            "bot": {
                "key": "github_key",
            },
        }
    }
    mock_configuration.set_params(custom_params)
    return custom_params


def get_github_integration_token_side_effect(
    service: str,
    installation_id: int = None,
    app_id: str | None = None,
    pem_path: str | None = None,
):
    return f"installation_token_{installation_id}_{app_id}"


@pytest.fixture
def redis_connection():
    return get_redis_connection()


def test_determine_entity_redis_key_github_bot():
    assert determine_entity_redis_key(owner=None, repository=None) == "github_bot"


@patch(
    "shared.bots.github_apps.get_github_integration_token",
    side_effect=get_github_integration_token_side_effect,
)
@pytest.mark.django_db(databases={"default"})
def test_determine_entity_redis_key_installed_gh_app_via_repository(
    mock_get_github_integration_token,
):
    owner = OwnerFactory(
        service="github",
        bot=None,
        unencrypted_oauth_token="owner_token: :refresh_token",
    )
    owner.save()
    gh_app = GithubAppInstallation(
        repository_service_ids=None,
        installation_id=1200,
        name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
        app_id=200,
        pem_path="pem_path",
        created_at=datetime.datetime.now(datetime.UTC),
        owner=owner,
    )
    gh_app.save()
    repository = RepositoryFactory(author=owner, using_integration=None)
    repository.save()
    assert (
        determine_entity_redis_key(owner=owner, repository=repository)
        == f"{gh_app.app_id}_{gh_app.installation_id}"
    )


@patch(
    "shared.bots.github_apps.get_github_integration_token",
    side_effect=get_github_integration_token_side_effect,
)
@pytest.mark.django_db(databases={"default"})
def test_determine_entity_redis_key_installed_gh_app_via_owner(
    mock_get_github_integration_token,
):
    owner = OwnerFactory(
        service="github",
        bot=None,
        unencrypted_oauth_token="owner_token: :refresh_token",
    )
    owner.save()
    gh_app = GithubAppInstallation(
        repository_service_ids=None,
        installation_id=1200,
        name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
        app_id=200,
        pem_path="pem_path",
        created_at=datetime.datetime.now(datetime.UTC),
        owner=owner,
    )
    gh_app.save()
    repository = None
    assert (
        determine_entity_redis_key(owner=owner, repository=repository)
        == f"{gh_app.app_id}_{gh_app.installation_id}"
    )


@pytest.mark.django_db(databases={"default"})
def test_determine_entity_redis_key_owner_token_via_repository():
    owner = OwnerFactory(
        ownerid=1428,
        service="github",
        bot=None,
        unencrypted_oauth_token="owner_token: :refresh_token",
    )
    owner.save()
    repository = RepositoryFactory(author=owner, using_integration=None)
    repository.save()
    assert determine_entity_redis_key(owner=owner, repository=repository) == str(
        repository.author.ownerid
    )


@pytest.mark.django_db(databases={"default"})
def test_determine_entity_redis_key_owner_token_via_owner():
    owner = OwnerFactory(
        ownerid=1428,
        service="github",
        bot=None,
        unencrypted_oauth_token="owner_token: :refresh_token",
    )
    owner.save()
    repository = None
    assert determine_entity_redis_key(owner=owner, repository=repository) == str(
        owner.ownerid
    )


def test_determine_if_entity_is_rate_limited_true(redis_connection):
    key_name = "owner_id_123"
    set_entity_to_rate_limited(
        redis_connection=redis_connection, key_name=key_name, ttl_seconds=300
    )
    assert (
        determine_if_entity_is_rate_limited(
            redis_connection=redis_connection, key_name=key_name
        )
        == True
    )


def test_determine_if_entity_is_rate_limited_false(redis_connection):
    assert (
        determine_if_entity_is_rate_limited(
            redis_connection=redis_connection,
            key_name="random_non_existent_key",
        )
        == False
    )


def test_determine_if_entity_is_rate_limited_error(redis_connection, mocker):
    mock_redis = MagicMock(name="fake_redis")
    mock_redis.exists.side_effect = RedisError
    assert (
        determine_if_entity_is_rate_limited(
            redis_connection=redis_connection,
            key_name="random_non_existent_key",
        )
        == False
    )


def test_set_entity_to_rate_limited_success(redis_connection):
    key_name = "owner_id_123"
    set_entity_to_rate_limited(
        redis_connection=redis_connection, key_name=key_name, ttl_seconds=300
    )
    assert redis_connection.get(f"rate_limited_entity_{key_name}") is not None


def test_set_entity_to_rate_limited_error(redis_connection, mocker):
    mock_redis = MagicMock(name="fake_redis")
    mock_redis.set.side_effect = RedisError
    key_name = "owner_id_123"
    # This actually asserts that the error is not raised
    # Despite the call failing
    set_entity_to_rate_limited(
        redis_connection=redis_connection, key_name=key_name, ttl_seconds=300
    )
    mock_redis.set.assert_not_called()


def test_set_entity_to_rate_limited_ttl_zero(redis_connection):
    key_name = "owner_id_123"
    # This actually asserts that the error is not raised
    # Despite the call failing
    set_entity_to_rate_limited(
        redis_connection=redis_connection, key_name=key_name, ttl_seconds=0
    )
    assert redis_connection.get(f"rate_limited_entity_{key_name}") is not None


@pytest.mark.parametrize(
    "app_id, installation_id, expected",
    [
        (200, 718263, "200_718263"),
        (None, 718263, "default_app_718263"),
    ],
)
def test_gh_app_key_name_with_or_without_id(app_id, installation_id, expected):
    assert (
        gh_app_key_name(
            app_id=app_id,
            installation_id=installation_id,
        )
        == expected
    )
