import pytest

from shared.bots.exceptions import RepositoryWithoutValidBotError
from shared.bots.github_apps import get_github_app_info_for_owner
from shared.bots.repo_bots import get_repo_appropriate_bot_token
from shared.django_apps.codecov_auth.models import (
    GITHUB_APP_INSTALLATION_DEFAULT_NAME,
    GithubAppInstallation,
)
from shared.django_apps.core.tests.factories import RepositoryFactory
from shared.github import InvalidInstallationError

fake_private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDCFqq2ygFh9UQU/6PoDJ6L9e4ovLPCHtlBt7vzDwyfwr3XGxln
0VbfycVLc6unJDVEGZ/PsFEuS9j1QmBTTEgvCLR6RGpfzmVuMO8wGVEO52pH73h9
rviojaheX/u3ZqaA0di9RKy8e3L+T0ka3QYgDx5wiOIUu1wGXCs6PhrtEwICBAEC
gYBu9jsi0eVROozSz5dmcZxUAzv7USiUcYrxX007SUpm0zzUY+kPpWLeWWEPaddF
VONCp//0XU8hNhoh0gedw7ZgUTG6jYVOdGlaV95LhgY6yXaQGoKSQNNTY+ZZVT61
zvHOlPynt3GZcaRJOlgf+3hBF5MCRoWKf+lDA5KiWkqOYQJBAMQp0HNVeTqz+E0O
6E0neqQDQb95thFmmCI7Kgg4PvkS5mz7iAbZa5pab3VuyfmvnVvYLWejOwuYSp0U
9N8QvUsCQQD9StWHaVNM4Lf5zJnB1+lJPTXQsmsuzWvF3HmBkMHYWdy84N/TdCZX
Cxve1LR37lM/Vijer0K77wAx2RAN/ppZAkB8+GwSh5+mxZKydyPaPN29p6nC6aLx
3DV2dpzmhD0ZDwmuk8GN+qc0YRNOzzJ/2UbHH9L/lvGqui8I6WLOi8nDAkEA9CYq
ewfdZ9LcytGz7QwPEeWVhvpm0HQV9moetFWVolYecqBP4QzNyokVnpeUOqhIQAwe
Z0FJEQ9VWsG+Df0noQJBALFjUUZEtv4x31gMlV24oiSWHxIRX4fEND/6LpjleDZ5
C/tY+lZIEO1Gg/FxSMB+hwwhwfSuE3WohZfEcSy+R48=
-----END RSA PRIVATE KEY-----"""


class TestRepositoryServiceIntegration(object):
    @pytest.mark.django_db(databases={"default"})
    def test_get_token_type_mapping_non_existing_integration(
        self, codecov_vcr, mock_configuration, mocker
    ):
        # this test was done with valid integration_id, pem and then the data was scrubbed
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        mock_configuration._params = {"github": {"integration": {"id": 123}}}
        repo = RepositoryFactory(
            author__username="ThiagoCodecov",
            author__service="github",
            author__integration_id=5944641,
            name="example-python",
            using_integration=True,
            private=True,
            author__oauth_token=None,
        )
        repo.save()
        with pytest.raises(RepositoryWithoutValidBotError):
            get_repo_appropriate_bot_token(repo)

    @pytest.mark.django_db(databases={"default"})
    def test_get_token_type_mapping_bad_data(
        self, codecov_vcr, mock_configuration, mocker
    ):
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        mock_configuration._params = {"github": {"integration": {"id": 999}}}
        repo = RepositoryFactory(
            author__username="ThiagoCodecov",
            author__service="github",
            author__integration_id=None,
            name="example-python",
            using_integration=False,
        )
        repo.save()
        app = GithubAppInstallation(
            repository_service_ids=None,
            installation_id=5944641,
            app_id=999,
            name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
            owner=repo.author,
        )
        app.save()
        assert list(repo.author.github_app_installations.all()) == [app]
        with pytest.raises(InvalidInstallationError):
            info = get_github_app_info_for_owner(repo.author)
            get_repo_appropriate_bot_token(repo, info[0])
