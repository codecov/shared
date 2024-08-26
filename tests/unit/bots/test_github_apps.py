import datetime

import pytest

from shared.bots.exceptions import NoConfiguredAppsAvailable, RequestedGithubAppNotFound
from shared.bots.github_apps import (
    get_github_app_info_for_owner,
    get_github_app_token,
    get_specific_github_app_details,
)
from shared.django_apps.codecov_auth.models import (
    GITHUB_APP_INSTALLATION_DEFAULT_NAME,
    GithubAppInstallation,
    Owner,
    Service,
)
from shared.django_apps.codecov_auth.tests.factories import OwnerFactory
from shared.github import InvalidInstallationError
from shared.typings.torngit import GithubInstallationInfo


def _get_owner_with_apps() -> Owner:
    owner = OwnerFactory(service="github")
    app_1 = GithubAppInstallation(
        owner=owner,
        installation_id=1200,
        app_id=12,
    )
    app_2 = GithubAppInstallation(
        owner=owner,
        installation_id=1500,
        app_id=15,
        pem_path="some_path",
    )
    GithubAppInstallation.objects.bulk_create([app_1, app_2])
    assert list(owner.github_app_installations.all()) == [app_1, app_2]
    return owner


def _to_installation_info(
    installation: GithubAppInstallation,
) -> GithubInstallationInfo:
    return GithubInstallationInfo(
        id=installation.id,
        installation_id=installation.installation_id,
        pem_path=installation.pem_path,
        app_id=installation.app_id,
    )


class TestGetSpecificGithubAppDetails(object):
    @pytest.mark.django_db(databases={"default"})
    def test_get_specific_github_app_details(self):
        owner = _get_owner_with_apps()
        assert get_specific_github_app_details(
            owner, owner.github_app_installations.all()[0].id, "commit_id_for_logs"
        ) == GithubInstallationInfo(
            id=owner.github_app_installations.all()[0].id,
            installation_id=1200,
            app_id=12,
            pem_path=None,
        )
        assert get_specific_github_app_details(
            owner, owner.github_app_installations.all()[1].id, "commit_id_for_logs"
        ) == GithubInstallationInfo(
            id=owner.github_app_installations.all()[1].id,
            installation_id=1500,
            app_id=15,
            pem_path="some_path",
        )

    @pytest.mark.django_db(databases={"default"})
    def test_get_specific_github_app_not_found(self):
        owner = _get_owner_with_apps()
        with pytest.raises(RequestedGithubAppNotFound):
            get_specific_github_app_details(owner, 123456, "commit_id_for_logs")

    @pytest.mark.parametrize(
        "app, is_rate_limited",
        [
            pytest.param(
                GithubAppInstallation(
                    repository_service_ids=None,
                    installation_id=1400,
                    name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
                    app_id=400,
                    pem_path="pem_path",
                    created_at=datetime.datetime.now(datetime.UTC),
                    is_suspended=True,
                ),
                False,
                id="suspended_app",
            ),
            pytest.param(
                GithubAppInstallation(
                    repository_service_ids=None,
                    installation_id=1400,
                    name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
                    app_id=400,
                    pem_path="pem_path",
                    created_at=datetime.datetime.now(datetime.UTC),
                    is_suspended=False,
                ),
                True,
                id="rate_limited_app",
            ),
        ],
    )
    @pytest.mark.django_db(databases={"default"})
    def test_raise_NoAppsConfiguredAvailable_if_suspended_or_rate_limited(
        self, app, is_rate_limited, mocker
    ):
        owner = OwnerFactory(
            service="github",
            bot=None,
            unencrypted_oauth_token="owner_token: :refresh_token",
        )
        owner.save()

        app.owner = owner
        app.save()

        mock_is_rate_limited = mocker.patch(
            "shared.bots.github_apps.determine_if_entity_is_rate_limited",
            return_value=is_rate_limited,
        )
        with pytest.raises(NoConfiguredAppsAvailable) as exp:
            get_github_app_info_for_owner(owner)
        mock_is_rate_limited.assert_called()
        assert exp.value.apps_count == 1
        assert exp.value.suspended_count == int(app.is_suspended)
        assert exp.value.rate_limited_count == int(is_rate_limited)


class TestGettingGitHubAppTokenSideEffect(object):
    @pytest.mark.django_db(databases={"default"})
    def test_mark_installation_suspended_side_effect(self, mocker):
        owner = _get_owner_with_apps()
        installations: list[GithubAppInstallation] = (
            owner.github_app_installations.all()
        )
        installation_info = _to_installation_info(installations[0])
        mocker.patch(
            "shared.bots.github_apps.get_github_integration_token",
            side_effect=InvalidInstallationError("installation_suspended"),
        )

        assert all(
            [installation.is_suspended == False for installation in installations]
        )

        with pytest.raises(InvalidInstallationError):
            get_github_app_token(Service(owner.service), installation_info)

        installations[0].refresh_from_db()
        assert installations[0].is_suspended is True
        installations[1].refresh_from_db()
        assert installations[1].is_suspended is False

    @pytest.mark.django_db(databases={"default"})
    def test_mark_installation_suspended_side_effect_not_called(self, mocker):
        owner = _get_owner_with_apps()
        installations: list[GithubAppInstallation] = (
            owner.github_app_installations.all()
        )
        installation_info = _to_installation_info(installations[0])
        mocker.patch(
            "shared.bots.github_apps.get_github_integration_token",
            side_effect=InvalidInstallationError("permission_error"),
        )

        assert all(
            [installation.is_suspended == False for installation in installations]
        )

        with pytest.raises(InvalidInstallationError):
            get_github_app_token(Service(owner.service), installation_info)

        installations[0].refresh_from_db()
        installations[1].refresh_from_db()
        assert all(
            [installation.is_suspended == False for installation in installations]
        )
