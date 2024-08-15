import pytest

from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.codecov_auth.tests.factories import (
    AccountFactory,
    OktaSettingsFactory,
    OwnerFactory,
)
from shared.django_apps.core.models import Repository
from shared.django_apps.core.tests.factories import RepositoryFactory


@pytest.fixture
def user_owner(viewable_repo_by_permission: Repository) -> Owner:
    owner = OwnerFactory(permission=[viewable_repo_by_permission.repoid])
    owner.save()
    return owner


@pytest.fixture
def viewable_repo_by_authorship(user_owner: Owner) -> Repository:
    repo = RepositoryFactory(author=user_owner, private=True)
    repo.save()
    return repo


@pytest.fixture
def viewable_repo_by_permission() -> Repository:
    repo = RepositoryFactory(private=True)
    repo.save()
    return repo


@pytest.fixture
def unviewable_repo() -> Repository:
    repo = RepositoryFactory()
    repo.save()
    return repo


@pytest.mark.django_db
def test_repository_queryset_viewable_repos(
    user_owner: Owner,
    unviewable_repo: Repository,
    viewable_repo_by_authorship: Repository,
    viewable_repo_by_permission: Repository,
):
    all_queryset = Repository.objects.all()
    assert all_queryset.count() == 3

    # filters out the unviewable repo, which is the repo that has neither permissions nor
    # authorship related to the user.
    viewable_repos = all_queryset.viewable_repos(user_owner)
    assert viewable_repos.count() == 2


@pytest.mark.django_db
def test_repository_queryset_exclude_accounts_enforced_okta(user_owner: Owner):
    account = AccountFactory()
    org_owner = OwnerFactory(account=account)
    org_owner.save()
    okta_settings = OktaSettingsFactory(account=account, enforced=True)
    okta_settings.save()

    repo = RepositoryFactory(author=org_owner, private=True)
    repo.save()

    all_queryset = Repository.objects.filter(author=org_owner)
    assert all_queryset.count() == 1

    filtered_queryset = all_queryset.exclude_accounts_enforced_okta([])
    assert filtered_queryset.count() == 0


@pytest.mark.parametrize(
    "is_private,has_account,has_okta,enforced_okta,is_authenticated",
    [
        pytest.param(False, False, False, False, False, id="not private repo"),
        pytest.param(True, False, False, False, False, id="no account"),
        pytest.param(True, True, False, False, False, id="no okta settings"),
        pytest.param(True, True, True, False, False, id="not enforced okta"),
        pytest.param(True, True, True, True, True, id="is authenticated"),
    ],
)
@pytest.mark.django_db
def test_repository_queryset_exclude_accounts_enforced_okta_do_not_exclude(
    user_owner: Owner,
    is_private: bool,
    has_account: bool,
    has_okta: bool,
    enforced_okta: bool,
    is_authenticated: bool,
):
    org_owner = OwnerFactory()
    repo = RepositoryFactory(author=org_owner, private=is_private)
    repo.save()

    authenticated_accounts = []

    if has_account:
        account = AccountFactory()
        org_owner.account = account
        org_owner.save()

        if has_okta:
            okta_settings = OktaSettingsFactory(account=account, enforced=enforced_okta)
            okta_settings.save()

        if is_authenticated:
            authenticated_accounts.append(account.id)

    all_queryset = Repository.objects.filter(author=org_owner)
    assert all_queryset.count() == 1

    filtered_queryset = all_queryset.exclude_accounts_enforced_okta(
        authenticated_accounts
    )
    assert filtered_queryset.count() == 1
