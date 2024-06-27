import pytest
from shared.typings.torngit import GithubInstallationInfo

from shared.django_apps.codecov_auth.models import GithubAppInstallation
from shared.django_apps.codecov_auth.tests.factories import OwnerFactory
from shared.bots.exceptions import RequestedGithubAppNotFound
from shared.bots.github_apps import get_specific_github_app_details


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
