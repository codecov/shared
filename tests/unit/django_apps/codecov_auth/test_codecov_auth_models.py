import logging
from dataclasses import asdict
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.forms import ValidationError
from django.test import TransactionTestCase
from pytest import LogCaptureFixture

from shared.django_apps.codecov_auth.models import (
    DEFAULT_AVATAR_SIZE,
    GITHUB_APP_INSTALLATION_DEFAULT_NAME,
    INFINITY,
    SERVICE_BITBUCKET,
    SERVICE_BITBUCKET_SERVER,
    SERVICE_CODECOV_ENTERPRISE,
    SERVICE_GITHUB,
    SERVICE_GITHUB_ENTERPRISE,
    Account,
    AccountsUsers,
    GithubAppInstallation,
    OrganizationLevelToken,
    Owner,
    Service,
    User,
)
from shared.django_apps.codecov_auth.tests.factories import (
    AccountFactory,
    InvoiceBillingFactory,
    OktaSettingsFactory,
    OrganizationLevelTokenFactory,
    OwnerFactory,
    StripeBillingFactory,
    UserFactory,
)
from shared.django_apps.core.tests.factories import RepositoryFactory
from shared.plan.constants import BASIC_PLAN, PlanName
from shared.utils.test_utils import mock_config_helper


class TestOwnerModel(TransactionTestCase):
    def setUp(self):
        self.owner = OwnerFactory(username="codecov_name", email="name@codecov.io")

    def test_repo_total_credits_returns_correct_repos_for_legacy_plan(self):
        self.owner.plan = "5m"
        assert self.owner.repo_total_credits == 5

    def test_repo_total_credits_returns_correct_repos_for_v4_plan(self):
        self.owner.plan = "v4-100m"
        assert self.owner.repo_total_credits == 100

    def test_repo_total_credits_returns_infinity_for_user_plans(self):
        users_plans = ("users", "users-inappm", "users-inappy", "users-free")
        for plan in users_plans:
            self.owner.plan = plan
            assert self.owner.repo_total_credits == INFINITY

    def test_repo_credits_accounts_for_currently_active_private_repos(self):
        self.owner.plan = "5m"
        RepositoryFactory(author=self.owner, active=True, private=True)

        assert self.owner.repo_credits == 4

    def test_repo_credits_ignores_active_public_repos(self):
        self.owner.plan = "5m"
        RepositoryFactory(author=self.owner, active=True, private=True)
        RepositoryFactory(author=self.owner, active=True, private=False)

        assert self.owner.repo_credits == 4

    def test_repo_credits_returns_infinity_for_user_plans(self):
        users_plans = ("users", "users-inappm", "users-inappy", "users-free")
        for plan in users_plans:
            self.owner.plan = plan
            assert self.owner.repo_credits == INFINITY

    def test_repo_credits_treats_null_plan_as_free_plan(self):
        self.owner.plan = None
        self.owner.save()
        assert self.owner.repo_credits == 1 + self.owner.free or 0

    def test_nb_active_private_repos(self):
        owner = OwnerFactory()
        RepositoryFactory(author=owner, active=True, private=True)
        RepositoryFactory(author=owner, active=True, private=False)
        RepositoryFactory(author=owner, active=False, private=True)
        RepositoryFactory(author=owner, active=False, private=False)

        assert owner.nb_active_private_repos == 1

    def test_plan_is_null_when_validating_form(self):
        owner = OwnerFactory()
        owner.plan = ""
        owner.stripe_customer_id = ""
        owner.stripe_subscription_id = ""
        owner.clean()
        assert owner.plan is None
        assert owner.stripe_customer_id is None
        assert owner.stripe_subscription_id is None

    def test_setting_staff_on_for_not_a_codecov_member(self):
        user_not_part_of_codecov = OwnerFactory(email="user@notcodecov.io", staff=True)
        with self.assertRaises(ValidationError):
            user_not_part_of_codecov.clean()

    def test_setting_staff_on_with_email_null(self):
        user_with_null_email = OwnerFactory(email=None, staff=True)
        with self.assertRaises(ValidationError):
            user_with_null_email.clean()

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_main_avatar_url_services(self, mock_get_config):
        test_cases = [
            {
                "service": SERVICE_GITHUB,
                "get_config": None,
                "expected": f"https://avatars0.githubusercontent.com/u/{self.owner.service_id}?v=3&s={DEFAULT_AVATAR_SIZE}",
            },
            {
                "service": SERVICE_GITHUB_ENTERPRISE,
                "get_config": "github_enterprise",
                "expected": f"github_enterprise/avatars/u/{self.owner.service_id}?v=3&s={DEFAULT_AVATAR_SIZE}",
            },
            {
                "service": SERVICE_BITBUCKET,
                "get_config": None,
                "expected": f"https://bitbucket.org/account/codecov_name/avatar/{DEFAULT_AVATAR_SIZE}",
            },
        ]
        for i in range(0, len(test_cases)):
            with self.subTest(i=i):
                mock_get_config.return_value = test_cases[i]["get_config"]
                self.owner.service = test_cases[i]["service"]
                self.assertEqual(self.owner.avatar_url, test_cases[i]["expected"])

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_bitbucket_without_u_url(self, mock_get_config):
        def side_effect(*args):
            if (
                len(args) == 2
                and args[0] == SERVICE_BITBUCKET_SERVER
                and args[1] == "url"
            ):
                return SERVICE_BITBUCKET_SERVER

        mock_get_config.side_effect = side_effect
        self.owner.service = SERVICE_BITBUCKET_SERVER
        self.assertEqual(
            self.owner.avatar_url,
            f"bitbucket_server/projects/codecov_name/avatar.png?s={DEFAULT_AVATAR_SIZE}",
        )

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_bitbucket_with_u_url(self, mock_get_config):
        def side_effect(*args):
            if (
                len(args) == 2
                and args[0] == SERVICE_BITBUCKET_SERVER
                and args[1] == "url"
            ):
                return SERVICE_BITBUCKET_SERVER

        mock_get_config.side_effect = side_effect
        self.owner.service = SERVICE_BITBUCKET_SERVER
        self.owner.service_id = "U1234"
        self.assertEqual(
            self.owner.avatar_url,
            f"bitbucket_server/users/codecov_name/avatar.png?s={DEFAULT_AVATAR_SIZE}",
        )

    @patch("shared.django_apps.codecov_auth.models.get_gitlab_url")
    def test_gitlab_service(self, mock_gitlab_url):
        mock_gitlab_url.return_value = "gitlab_url"
        self.owner.service = "gitlab"
        self.assertEqual(self.owner.avatar_url, "gitlab_url")
        mock_gitlab_url.assert_called_once()

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_gravatar_url(self, mock_get_config):
        def side_effect(*args):
            if len(args) == 2 and args[0] == "services" and args[1] == "gravatar":
                return "gravatar"

        mock_get_config.side_effect = side_effect
        self.owner.service = None
        self.assertEqual(
            self.owner.avatar_url,
            f"https://www.gravatar.com/avatar/9a74a018e6162103a2845e22ec5d88ef?s={DEFAULT_AVATAR_SIZE}",
        )

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_avatario_url(self, mock_get_config):
        def side_effect(*args):
            if len(args) == 2 and args[0] == "services" and args[1] == "avatars.io":
                return "avatars.io"

        mock_get_config.side_effect = side_effect
        self.owner.service = None
        self.assertEqual(
            self.owner.avatar_url,
            f"https://avatars.io/avatar/9a74a018e6162103a2845e22ec5d88ef/{DEFAULT_AVATAR_SIZE}",
        )

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_ownerid_url(self, mock_get_config):
        def side_effect(*args):
            if len(args) == 2 and args[0] == "setup" and args[1] == "codecov_url":
                return "codecov_url"

        mock_get_config.side_effect = side_effect
        self.owner.service = None
        self.assertEqual(
            self.owner.avatar_url,
            f"codecov_url/users/{self.owner.ownerid}.png?size={DEFAULT_AVATAR_SIZE}",
        )

    @patch("shared.django_apps.codecov_auth.models.get_config")
    @patch("shared.django_apps.codecov_auth.models.os.getenv")
    def test_service_codecov_enterprise_url(self, mock_getenv, mock_get_config):
        def side_effect(*args):
            if len(args) == 2 and args[0] == "setup" and args[1] == "codecov_url":
                return "codecov_url"

        mock_get_config.side_effect = side_effect
        mock_getenv.return_value = SERVICE_CODECOV_ENTERPRISE
        self.owner.service = None
        self.owner.ownerid = None
        self.assertEqual(
            self.owner.avatar_url, "codecov_url/media/images/gafsi/avatar.svg"
        )

    @patch("shared.django_apps.codecov_auth.models.get_config")
    def test_service_codecov_media_url(self, mock_get_config):
        def side_effect(*args):
            if (
                len(args) == 3
                and args[0] == "setup"
                and args[1] == "media"
                and args[2] == "assets"
            ):
                return "codecov_url_media"

        mock_get_config.side_effect = side_effect
        self.owner.service = None
        self.owner.ownerid = None
        self.assertEqual(
            self.owner.avatar_url, "codecov_url_media/media/images/gafsi/avatar.svg"
        )

    def test_is_admin_returns_false_if_admin_array_is_null(self):
        assert self.owner.is_admin(OwnerFactory()) is False

    def test_is_admin_returns_true_when_comparing_with_self(self):
        assert self.owner.is_admin(self.owner) is True

    def test_is_admin_returns_true_if_ownerid_in_admin_array(self):
        owner = OwnerFactory()
        self.owner.admins = [owner.ownerid]
        assert self.owner.is_admin(owner) is True

    def test_is_admin_returns_false_if_ownerid_not_in_admin_array(self):
        owner = OwnerFactory()
        self.owner.admins = []
        assert self.owner.is_admin(owner) is False

    def test_activated_user_count_returns_num_activated_users(self):
        owner = OwnerFactory(
            plan_activated_users=[OwnerFactory().ownerid, OwnerFactory().ownerid]
        )
        assert owner.activated_user_count == 2

    def test_activated_user_count_returns_0_if_plan_activated_users_is_null(self):
        owner = OwnerFactory(plan_activated_users=None)
        assert owner.plan_activated_users is None
        assert owner.activated_user_count == 0

    def test_activated_user_count_ignores_students(self):
        student = OwnerFactory(student=True)
        self.owner.plan_activated_users = [student.ownerid]
        self.owner.save()
        assert self.owner.activated_user_count == 0

    def test_activate_user_adds_ownerid_to_plan_activated_users(self):
        to_activate = OwnerFactory()
        self.owner.activate_user(to_activate)
        self.owner.refresh_from_db()
        assert to_activate.ownerid in self.owner.plan_activated_users

    def test_activate_user_does_nothing_if_user_is_activated(self):
        to_activate = OwnerFactory()
        self.owner.plan_activated_users = [to_activate.ownerid]
        self.owner.save()
        self.owner.activate_user(to_activate)
        self.owner.refresh_from_db()
        assert self.owner.plan_activated_users == [to_activate.ownerid]

    def test_activate_user_updates_account_user(self):
        to_activate = OwnerFactory()
        account = AccountFactory()
        self.owner.account = account
        self.owner.save()

        self.owner.activate_user(to_activate)
        self.owner.refresh_from_db()

        assert to_activate.ownerid in self.owner.plan_activated_users
        user = to_activate.user
        assert AccountsUsers.objects.filter(user=user, account=account).first()

    def test_deactivate_removes_ownerid_from_plan_activated_users(self):
        to_deactivate = OwnerFactory()
        self.owner.plan_activated_users = [3, 4, to_deactivate.ownerid]
        self.owner.save()
        self.owner.deactivate_user(to_deactivate)
        self.owner.refresh_from_db()
        assert to_deactivate.ownerid not in self.owner.plan_activated_users

    def test_deactivate_non_activated_user_doesnt_crash(self):
        to_deactivate = OwnerFactory()
        self.owner.plan_activated_users = []
        self.owner.save()
        self.owner.deactivate_user(to_deactivate)

    def test_deactivate_user_updates_account_user(self):
        owner_org = self.owner
        to_deactivate = OwnerFactory()
        owner_org.account = AccountFactory()
        to_deactivate.user = UserFactory()
        owner_org.save()
        AccountsUsers(user=to_deactivate.user, account=self.owner.account).save()

        owner_org.deactivate_user(to_deactivate)
        owner_org.refresh_from_db()

        assert (
            AccountsUsers.objects.filter(
                user=to_deactivate.user, account=self.owner.account
            ).first()
            is None
        )

    def test_can_activate_user_returns_true_if_user_is_student(self):
        student = OwnerFactory(student=True)
        assert self.owner.can_activate_user(student) is True

    def test_can_activate_user_returns_true_if_activated_user_count_not_maxed(self):
        to_activate = OwnerFactory()
        existing_user = OwnerFactory(ownerid=1000, student=False)
        self.owner.plan_activated_users = [existing_user.ownerid]
        self.owner.plan_user_count = 2
        self.owner.save()
        assert self.owner.can_activate_user(to_activate) is True

    def test_can_activate_user_factors_free_seats_into_total_allowed(self):
        to_activate = OwnerFactory()
        self.owner.free = 1
        self.owner.plan_user_count = 0
        self.owner.save()
        assert self.owner.can_activate_user(to_activate) is True

    def test_can_activate_user_can_activate_account(self):
        self.owner.account = AccountFactory(plan_seat_count=1)
        self.owner.plan_user_count = 1
        self.owner.save()
        assert self.owner.can_activate_user(self.owner)

    def test_can_activate_user_cannot_activate_account(self):
        self.owner.account = AccountFactory(plan_seat_count=0)
        self.owner.plan_user_count = 1
        self.owner.save()
        assert not self.owner.can_activate_user(self.owner)

    def test_add_admin_adds_ownerid_to_admin_array(self):
        self.owner.admins = []
        self.owner.save()
        admin = OwnerFactory()
        self.owner.add_admin(admin)

        self.owner.refresh_from_db()
        assert admin.ownerid in self.owner.admins

    def test_add_admin_creates_array_if_null(self):
        self.owner.admins = None
        self.owner.save()
        admin = OwnerFactory()
        self.owner.add_admin(admin)

        self.owner.refresh_from_db()
        assert self.owner.admins == [admin.ownerid]

    def test_add_admin_doesnt_add_if_ownerid_already_in_admins(self):
        admin = OwnerFactory()
        self.owner.admins = [admin.ownerid]
        self.owner.save()

        self.owner.add_admin(admin)

        self.owner.refresh_from_db()
        assert self.owner.admins == [admin.ownerid]

    def test_remove_admin_removes_ownerid_from_admins(self):
        admin1 = OwnerFactory()
        admin2 = OwnerFactory()
        self.owner.admins = [admin1.ownerid, admin2.ownerid]
        self.owner.save()

        self.owner.remove_admin(admin1)

        self.owner.refresh_from_db()
        assert self.owner.admins == [admin2.ownerid]

    def test_remove_admin_does_nothing_if_user_not_admin(self):
        admin1 = OwnerFactory()
        admin2 = OwnerFactory()
        self.owner.admins = [admin1.ownerid]
        self.owner.save()

        self.owner.remove_admin(admin2)

        self.owner.refresh_from_db()
        assert self.owner.admins == [admin1.ownerid]

    def test_access_no_root_organization(self):
        assert self.owner.root_organization is None

    def test_access_root_organization(self):
        root = OwnerFactory(service="gitlab")
        parent = OwnerFactory(parent_service_id=root.service_id, service="gitlab")
        self.owner.parent_service_id = parent.service_id
        self.owner.service = "gitlab"
        self.owner.save()

        # In some cases, there will be a 4th query from OrganizationLevelToken. There's a hook that rnus after Owner is saved
        # To see if a org-wide token should be deleted. For cases when it should be deleted, the number of queries becomes 4
        with self.assertNumQueries(3):
            assert self.owner.root_organization == root

        # cache the root organization id
        assert self.owner.root_parent_service_id == root.service_id

        with self.assertNumQueries(1):
            self.owner.root_organization

    def test_inactive_users_count(self):
        org = OwnerFactory()

        activated_user = OwnerFactory()
        activated_user_in_org = OwnerFactory(organizations=[org.ownerid])
        activated_student = OwnerFactory(student=True)
        activated_student_in_org = OwnerFactory(
            organizations=[org.ownerid], student=True
        )

        OwnerFactory(organizations=[org.ownerid], student=True)
        OwnerFactory(organizations=[org.ownerid])

        org.plan_activated_users = [
            activated_user.ownerid,
            activated_user_in_org.ownerid,
            activated_student.ownerid,
            activated_student_in_org.ownerid,
        ]
        org.save()

        self.assertEqual(org.inactive_user_count, 1)

    def test_student_count(self):
        org = OwnerFactory(service=Service.GITHUB.value, service_id="1")

        activated_user = OwnerFactory()
        activated_user_in_org = OwnerFactory(organizations=[org.ownerid])
        activated_student = OwnerFactory(student=True)
        activated_student_in_org = OwnerFactory(
            organizations=[org.ownerid], student=True
        )

        OwnerFactory(organizations=[org.ownerid], student=True)
        OwnerFactory(organizations=[org.ownerid])

        org.plan_activated_users = [
            activated_user.ownerid,
            activated_user_in_org.ownerid,
            activated_student.ownerid,
            activated_student_in_org.ownerid,
        ]
        org.save()

        self.assertEqual(org.student_count, 3)

    def test_has_yaml(self):
        org = OwnerFactory(yaml=None)
        assert org.has_yaml is False
        org.yaml = {"require_ci_to_pass": True}
        org.save()
        assert org.has_yaml is True


class TestOrganizationLevelTokenModel(TransactionTestCase):
    def test_can_save_org_token_for_org_basic_plan(self):
        owner = OwnerFactory(plan="users-basic")
        owner.save()
        token = OrganizationLevelToken(owner=owner)
        token.save()
        assert OrganizationLevelToken.objects.filter(owner=owner).count() == 1

    @patch(
        "shared.django_apps.codecov_auth.services.org_level_token_service.OrgLevelTokenService.org_can_have_upload_token"
    )
    def test_token_is_deleted_when_changing_user_plan(
        self, mocked_org_can_have_upload_token
    ):
        mocked_org_can_have_upload_token.return_value = False
        owner = OwnerFactory(plan="users-enterprisem")
        org_token = OrganizationLevelTokenFactory(owner=owner)
        owner.save()
        org_token.save()
        assert OrganizationLevelToken.objects.filter(owner=owner).count() == 1
        owner.plan = "users-basic"
        owner.save()
        assert OrganizationLevelToken.objects.filter(owner=owner).count() == 0


class TestGithubAppInstallationModel(TransactionTestCase):
    DEFAULT_APP_ID = 12345

    @pytest.fixture(autouse=True)
    def mock_default_app_id(self, mocker):
        mock_config_helper(
            mocker, configs={"github.integration.id": self.DEFAULT_APP_ID}
        )

    def test_covers_all_repos(self):
        owner = OwnerFactory()
        repo1 = RepositoryFactory(author=owner)
        repo2 = RepositoryFactory(author=owner)
        repo3 = RepositoryFactory(author=owner)
        other_repo_different_owner = RepositoryFactory()
        installation_obj = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            installation_id=100,
        )
        installation_obj.save()
        assert installation_obj.name == "codecov_app_installation"
        assert installation_obj.covers_all_repos() == True
        assert installation_obj.is_repo_covered_by_integration(repo1) == True
        assert (
            installation_obj.is_repo_covered_by_integration(other_repo_different_owner)
            == False
        )
        assert list(owner.github_app_installations.all()) == [installation_obj]
        assert installation_obj.repository_queryset().exists()
        assert set(installation_obj.repository_queryset().all()) == set(
            [repo1, repo2, repo3]
        )

    def test_covers_some_repos(self):
        owner = OwnerFactory()
        repo = RepositoryFactory(author=owner)
        same_owner_other_repo = RepositoryFactory(author=owner)
        other_repo_different_owner = RepositoryFactory()
        installation_obj = GithubAppInstallation(
            owner=owner,
            repository_service_ids=[repo.service_id],
            installation_id=100,
        )
        installation_obj.save()
        assert installation_obj.covers_all_repos() == False
        assert installation_obj.is_repo_covered_by_integration(repo) == True
        assert (
            installation_obj.is_repo_covered_by_integration(other_repo_different_owner)
            == False
        )
        assert (
            installation_obj.is_repo_covered_by_integration(same_owner_other_repo)
            == False
        )
        assert list(owner.github_app_installations.all()) == [installation_obj]
        assert installation_obj.repository_queryset().exists()
        assert list(installation_obj.repository_queryset().all()) == [repo]

    def test_is_configured(self):
        owner = OwnerFactory()
        installation_default = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            installation_id=123,
            app_id=self.DEFAULT_APP_ID,
            name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
        )
        installation_configured = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            name="my_installation",
            installation_id=100,
            app_id=123,
            pem_path="some_path",
        )
        installation_not_configured = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            installation_id=100,
            name="my_other_installation",
            app_id=1234,
        )
        installation_default_name_not_configured = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            installation_id=100,
            app_id=121212,
            name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
        )
        installation_default_name_not_default_id_configured = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            installation_id=100,
            app_id=121212,
            name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
            pem_path="some_path",
        )
        installation_default.save()

        installation_configured.save()
        installation_not_configured.save()
        installation_default_name_not_configured.save()
        installation_default_name_not_default_id_configured.save()

        assert installation_default.is_configured() == True
        installation_default.app_id = str(self.DEFAULT_APP_ID)
        assert installation_default.is_configured() == True
        # Unconfigured apps are not configured
        installation_default.name = "unconfigured_app"
        assert installation_default.is_configured() == False

        assert installation_configured.is_configured() == True
        assert installation_not_configured.is_configured() == False
        assert installation_default_name_not_configured.app_id != self.DEFAULT_APP_ID
        assert installation_default_name_not_configured.is_configured() == False
        assert (
            installation_default_name_not_default_id_configured.app_id
            != self.DEFAULT_APP_ID
        )
        assert (
            installation_default_name_not_default_id_configured.is_configured() == True
        )


class TestGitHubAppInstallationNoDefaultAppIdConfig(TransactionTestCase):
    @pytest.fixture(autouse=True)
    def mock_no_default_app_id(self, mocker):
        mock_config_helper(mocker, configs={"github.integration.id": None})

    def test_is_configured_no_default(self):
        owner = OwnerFactory()
        installation_default = GithubAppInstallation(
            owner=owner,
            repository_service_ids=None,
            installation_id=123,
            app_id=1200,
            name=GITHUB_APP_INSTALLATION_DEFAULT_NAME,
        )
        installation_default.save()
        assert installation_default.is_configured() == True


class TestAccountModel(TransactionTestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog: LogCaptureFixture):
        self.caplog = caplog

    def test_account_with_billing_details(self):
        account = AccountFactory()
        OktaSettingsFactory(account=account)
        # set up stripe
        stripe = StripeBillingFactory(account=account)
        self.assertTrue(stripe.is_active)
        # switch to invoice
        invoice = InvoiceBillingFactory(account=account)
        stripe.refresh_from_db()
        invoice.refresh_from_db()
        self.assertTrue(invoice.is_active)
        self.assertFalse(stripe.is_active)
        # back to stripe
        stripe.is_active = True
        stripe.save()
        stripe.refresh_from_db()
        invoice.refresh_from_db()
        self.assertFalse(invoice.is_active)
        self.assertTrue(stripe.is_active)

    def test_account_with_users(self):
        user_1 = UserFactory()
        OwnerFactory(user=user_1)
        user_2 = UserFactory()
        OwnerFactory(user=user_2)
        account = AccountFactory()

        account.users.add(user_1)
        account.save()

        user_2.accounts.add(account)
        user_2.save()

        self.assertEqual(account.users.count(), 2)
        self.assertEqual(user_1.accounts.count(), 1)
        self.assertEqual(user_2.accounts.count(), 1)
        self.assertEqual(AccountsUsers.objects.all().count(), 2)

        # handles duplicates gracefully
        account.users.add(user_2)
        account.save()
        self.assertEqual(account.users.count(), 2)
        user_2.accounts.add(account)
        user_2.save()
        self.assertEqual(user_2.accounts.count(), 1)
        self.assertEqual(AccountsUsers.objects.all().count(), 2)

        # does not handle duplicates gracefully
        with self.assertRaises(IntegrityError):
            AccountsUsers.objects.create(user=user_1, account=account)
        self.assertEqual(account.users.count(), 2)
        self.assertEqual(user_1.accounts.count(), 1)
        self.assertEqual(AccountsUsers.objects.all().count(), 2)

        self.assertEqual(account.all_user_count, 2)
        self.assertEqual(account.organizations_count, 0)

        self.assertEqual(account.activated_student_count, 0)
        self.assertEqual(account.total_seat_count, 1)
        self.assertEqual(account.available_seat_count, 0)
        pretty_plan = asdict(BASIC_PLAN)
        pretty_plan.update({"quantity": 1})
        self.assertEqual(account.pretty_plan, pretty_plan)

    def test_create_account_for_enterprise_experience(self):
        # 2 separate OwnerOrgs that wish to Enterprise
        stripe_customer_id = "abc123"
        stripe_subscription_id = "defg456"

        user_for_owner_1 = UserFactory(email="hello@email.com", name="Luigi")
        owner_1 = OwnerFactory(
            username="codecov-1",
            plan=PlanName.BASIC_PLAN_NAME.value,
            plan_user_count=1,
            organizations=[],
            user_id=user_for_owner_1.id,  # has user
        )
        owner_2 = OwnerFactory(
            username="codecov-sentry",
            plan=PlanName.BASIC_PLAN_NAME.value,
            plan_user_count=1,
            organizations=[],
            user_id=None,  # no user
        )
        owner_3 = OwnerFactory(
            username="sentry-1",
            plan=PlanName.BASIC_PLAN_NAME.value,
            plan_user_count=1,
            organizations=[],
            user_id=None,  # no user
        )

        unrelated_owner = OwnerFactory(
            user_id=UserFactory().id,
            organizations=[],
        )
        unrelated_org = OwnerFactory(
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            plan=PlanName.CODECOV_PRO_YEARLY.value,
            plan_user_count=50,
            plan_activated_users=[unrelated_owner.ownerid],
        )
        unrelated_owner.organizations.append(unrelated_org.ownerid)
        unrelated_owner.save()

        org_1 = OwnerFactory(
            username="codecov-org",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            plan=PlanName.BASIC_PLAN_NAME.value,
            plan_user_count=50,
            plan_activated_users=[owner_1.ownerid, owner_2.ownerid],
            free=10,
        )
        org_2 = OwnerFactory(
            username="sentry-org",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            plan=PlanName.CODECOV_PRO_YEARLY.value,
            plan_user_count=50,
            plan_activated_users=[owner_2.ownerid, owner_3.ownerid],
            free=10,
        )
        owner_1.organizations.append(org_1.ownerid)
        owner_1.save()
        owner_2.organizations.extend([org_2.ownerid, org_1.ownerid])
        owner_2.save()
        owner_3.organizations.append(org_2.ownerid)
        owner_3.save()

        # How to Enterprise
        enterprise_account = AccountFactory(
            name="getsentry",
            plan=org_1.plan,
            plan_seat_count=org_1.plan_user_count,
            free_seat_count=org_1.free,
        )
        # create inactive Stripe billing
        StripeBillingFactory(
            account=enterprise_account,
            customer_id=stripe_customer_id,
            subscription_id=None,
            is_active=False,
        )
        # create active Invoice billing
        InvoiceBillingFactory(
            account=enterprise_account,
            account_manager="Mario",
        )

        org_1.account = enterprise_account
        org_1.save()
        org_2.account = enterprise_account
        org_2.save()
        enterprise_account.refresh_from_db()

        # connect Users to Account
        for org in [org_1, org_2]:
            for owner_user_id in org.plan_activated_users:
                owner_user = Owner.objects.get(ownerid=owner_user_id)
                if not owner_user.user_id:
                    # if the OwnerUser doesn't have a User obj, make one for them and attach to Owner object
                    user = UserFactory(
                        email=owner_user.email,
                        name=owner_user.name,
                    )
                    owner_user.user_id = user.id
                    owner_user.save()
                    enterprise_account.users.add(user)
                    enterprise_account.save()
                else:
                    enterprise_account.users.add(owner_user.user_id)

        enterprise_account.refresh_from_db()
        org_1.refresh_from_db()
        org_2.refresh_from_db()
        unrelated_org.refresh_from_db()
        owner_1.refresh_from_db()
        owner_2.refresh_from_db()
        owner_3.refresh_from_db()
        unrelated_owner.refresh_from_db()

        # for users
        for owner in [owner_1, owner_2, owner_3]:
            user = User.objects.get(id=owner.user_id)
            self.assertEqual(user.accounts.count(), 1)
            self.assertEqual(user.accounts.first(), enterprise_account)
            self.assertEqual(
                AccountsUsers.objects.get(user=user).account, enterprise_account
            )
        unrelated_user = User.objects.get(id=unrelated_owner.user_id)
        self.assertEqual(unrelated_user.accounts.count(), 0)
        self.assertIsNone(unrelated_user.accounts.first())
        self.assertFalse(AccountsUsers.objects.filter(user=unrelated_user).exists())

        # for orgs
        self.assertTrue(org_1.account)
        self.assertTrue(org_2.account)
        self.assertFalse(unrelated_org.account)
        self.assertEqual(org_1.account, enterprise_account)
        self.assertEqual(org_2.account, enterprise_account)
        self.assertEqual(
            set(
                enterprise_account.organizations.all().values_list("ownerid", flat=True)
            ),
            {org_1.ownerid, org_2.ownerid},
        )

        # for the enterprise account
        self.assertEqual(
            set(enterprise_account.users.all().values_list("id", flat=True)),
            {owner_1.user_id, owner_2.user_id, owner_3.user_id},
        )
        self.assertEqual(
            set(
                enterprise_account.organizations.all().values_list("ownerid", flat=True)
            ),
            {org_1.ownerid, org_2.ownerid},
        )
        self.assertTrue(
            AccountsUsers.objects.filter(account=enterprise_account).count(), 3
        )
        self.assertFalse(enterprise_account.stripe_billing.first().is_active)
        self.assertTrue(enterprise_account.invoice_billing.first().is_active)
        self.assertEqual(enterprise_account.all_user_count, 3)
        self.assertEqual(enterprise_account.organizations_count, 2)
        self.assertEqual(enterprise_account.activated_student_count, 0)
        self.assertEqual(enterprise_account.total_seat_count, 60)
        self.assertEqual(enterprise_account.available_seat_count, 57)
        pretty_plan = asdict(BASIC_PLAN)
        pretty_plan.update({"quantity": 50})
        self.assertEqual(enterprise_account.pretty_plan, pretty_plan)

    def test_activate_user_onto_account(self):
        user = UserFactory()
        user.save()
        account = AccountFactory()
        account.save()

        assert AccountsUsers.objects.filter(user=user, account=account).first() is None
        account.activate_user_onto_account(user)
        account.refresh_from_db()

        assert AccountsUsers.objects.filter(user=user, account=account).first()

    def test_activate_owner_user_onto_account_create_user(self):
        owner = OwnerFactory()
        account = AccountFactory()
        account.save()

        account.activate_owner_user_onto_account(owner)
        account.refresh_from_db()

        new_user = User.objects.get(id=owner.user_id)
        assert AccountsUsers.objects.filter(user=new_user, account=account).first()

    def test_activate_owner_user_onto_account_with_user(self):
        owner = OwnerFactory()
        user = UserFactory()
        owner.user = user
        account = AccountFactory()
        account.save()

        account.activate_owner_user_onto_account(owner)
        account.refresh_from_db()

        assert AccountsUsers.objects.filter(user=user, account=account).first()

    def test_activate_owner_user_onto_account_existing_account_user(self):
        owner = OwnerFactory()
        user = UserFactory()
        owner.user = user
        account = AccountFactory()
        account.save()

        account.activate_owner_user_onto_account(owner)
        account.refresh_from_db()

        assert AccountsUsers.objects.filter(user=user, account=account).first()

        account.activate_owner_user_onto_account(owner)
        account.refresh_from_db()

        assert AccountsUsers.objects.filter(user=user, account=account).first()

    def test_deactivate_owner_user_from_account_remove_user(self):
        # Set up User to be associated with an Org under an account
        owner = OwnerFactory()
        user = UserFactory()
        owner.user = user
        org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_YEARLY.value,
            plan_activated_users=[owner.ownerid],
        )
        account = AccountFactory()
        org.account = account
        org.save()
        account.users.add(user)
        account.save()

        # ensure that there exists an account user relationship before deactivating
        assert AccountsUsers.objects.filter(user=user, account=account).first()

        org.plan_activated_users = []
        org.save()
        account.deactivate_owner_user_from_account(owner)

        assert AccountsUsers.objects.filter(user=user, account=account).first() is None

    def test_deactivate_owner_user_from_account_do_not_remove_user(self):
        # Set up User to be associated with an Org under an account
        owner = OwnerFactory()
        user = UserFactory()
        owner.user = user
        org1 = OwnerFactory(
            plan=PlanName.CODECOV_PRO_YEARLY.value,
            plan_activated_users=[owner.ownerid],
        )
        org2 = OwnerFactory(
            plan=PlanName.CODECOV_PRO_YEARLY.value,
            plan_activated_users=[owner.ownerid],
        )
        account = AccountFactory()
        org1.account = account
        org1.save()
        org2.account = account
        org2.save()
        account.users.add(user)
        account.save()

        # ensure that there exists an account user relationship before deactivating
        assert AccountsUsers.objects.filter(user=user, account=account).first()

        # Only deactivate user for org1, org2 still has a reference to the user
        org1.plan_activated_users = []
        org1.save()
        account.deactivate_owner_user_from_account(owner)

        assert AccountsUsers.objects.filter(user=user, account=account).first()

    def test_deactivate_owner_user_no_user_do_nothing(self):
        owner_user = OwnerFactory(user=None)
        account = AccountFactory()
        account.save()
        with self.caplog.at_level(logging.WARNING):
            assert account.deactivate_owner_user_from_account(owner_user) is None
            assert (
                self.caplog.records[0].message
                == "Attempting to deactivate an owner without associated user. Skipping deactivation."
            )

    def test_activated_user_count(self):
        # This shouldn't show up on the account
        unrelated_owner: Owner = OwnerFactory(service="github")
        unrelated_user: User = UserFactory()
        unrelated_owner.user = unrelated_user
        unrelated_user.save()

        # This shouldn't show up because it's a student, and students don't
        # count towards activated users.
        student_owner: Owner = OwnerFactory(service="github", student=True)
        student_user: User = UserFactory()
        student_owner.user = student_user
        student_user.save()
        student_owner.save()

        # User1 also has multiple owners. Should be counted as 1 user
        owner1: Owner = OwnerFactory(service="github", student=False)
        owner1_gitlab: Owner = OwnerFactory(service="gitlab", student=False)
        owner1_bitbucket: Owner = OwnerFactory(service="bitbucket", student=False)
        user1: User = UserFactory()
        owner1.user = user1
        owner1_gitlab.user = user1
        owner1_bitbucket.user = user1
        owner1.save()
        owner1_gitlab.save()
        owner1_bitbucket.save()

        owner2: Owner = OwnerFactory(service="bitbucket", student=False)
        user2: User = UserFactory()
        owner2.user = user2
        owner2.save()

        org: Owner = OwnerFactory()
        account: Account = AccountFactory()
        org.account = account
        org.save()

        account.users.add(student_user)
        account.users.add(user1)
        account.users.add(user2)

        assert 2 == account.activated_user_count

    def test_can_activate_user_already_exist(self):
        owner: Owner = OwnerFactory(service="github", student=False)
        user: User = UserFactory()
        owner.user = user
        owner.save()
        user.save()

        org: Owner = OwnerFactory()
        account: Account = AccountFactory()
        org.account = account
        org.save()

        account.users.add(user)
        assert not account.can_activate_user(user)

    def test_can_activate_user_student(self):
        owner: Owner = OwnerFactory(service="github", student=True)
        user: User = UserFactory()
        owner.user = user
        owner.save()

        org: Owner = OwnerFactory()
        account: Account = AccountFactory(free_seat_count=0, plan_seat_count=0)
        org.account = account
        org.save()

        assert account.can_activate_user(user)

    def test_can_activate_user_not_enough_seats_left(self):
        owner: Owner = OwnerFactory(service="github", student=False)
        user: User = UserFactory()
        owner.user = user
        owner.save()

        org: Owner = OwnerFactory()
        account: Account = AccountFactory(free_seat_count=0, plan_seat_count=0)
        org.account = account
        org.save()

        assert not account.can_activate_user(user)

    def test_can_activate_user_enough_seats_left(self):
        owner: Owner = OwnerFactory(service="github", student=False)
        user: User = UserFactory()
        owner.user = user
        owner.save()

        org: Owner = OwnerFactory()
        account: Account = AccountFactory(free_seat_count=0, plan_seat_count=1)
        org.account = account
        org.save()

        assert account.can_activate_user(user)

    def test_can_activate_user_no_user(self):
        org: Owner = OwnerFactory()
        account: Account = AccountFactory(free_seat_count=0, plan_seat_count=1)
        org.account = account
        org.save()

        assert account.can_activate_user()


class TestUserModels(TransactionTestCase):
    def test_is_github_student(self):
        github_user: Owner = OwnerFactory(service="github", student=True)
        user = UserFactory()
        github_user.user = user
        github_user.save()

        assert user.is_github_student is True

    def test_is_not_github_student(self):
        github_user: Owner = OwnerFactory(service="github", student=False)
        user = UserFactory()
        github_user.user = user
        github_user.save()

        assert user.is_github_student is False

    def test_is_not_github_student_no_owners(self):
        user = UserFactory()

        assert user.is_github_student is False
