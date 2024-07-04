import datetime

import pytest
from shared.typings.torngit import GithubInstallationInfo

from shared.django_apps.codecov_auth.models import GithubAppInstallation, GITHUB_APP_INSTALLATION_DEFAULT_NAME
from shared.django_apps.codecov_auth.tests.factories import OwnerFactory
from shared.bots.exceptions import RequestedGithubAppNotFound, NoConfiguredAppsAvailable
from shared.bots.github_apps import get_specific_github_app_details, get_github_app_info_for_owner


class TestGetSpecificGithubAppDetails(object):
    def _get_owner_with_apps(self):
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

    @pytest.mark.django_db(databases={"default"})
    def test_get_specific_github_app_details(self):
        owner = self._get_owner_with_apps()
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
        owner = self._get_owner_with_apps()
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
            "shared.bots.github_apps.is_installation_rate_limited",
            return_value=is_rate_limited,
        )
        with pytest.raises(NoConfiguredAppsAvailable):
            get_github_app_info_for_owner(owner)
        mock_is_rate_limited.assert_called()
