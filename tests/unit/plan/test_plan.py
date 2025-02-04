from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from freezegun import freeze_time

from shared.django_apps.codecov.commands.exceptions import ValidationError
from shared.django_apps.codecov_auth.models import Service
from shared.django_apps.codecov_auth.tests.factories import (
    OwnerFactory,
    PlanFactory,
    TierFactory,
)
from shared.plan.constants import (
    DEFAULT_FREE_PLAN,
    FREE_PLAN_REPRESENTATIONS,
    TRIAL_PLAN_REPRESENTATION,
    TRIAL_PLAN_SEATS,
    PlanName,
    TierName,
    TrialDaysAmount,
    TrialStatus,
)
from shared.plan.service import PlanService
from tests.helper import mock_all_plans_and_tiers


@freeze_time("2023-06-19")
class PlanServiceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_all_plans_and_tiers()

    def test_plan_service_trial_status_not_started(self):
        current_org = OwnerFactory(plan=DEFAULT_FREE_PLAN)
        plan_service = PlanService(current_org=current_org)

        assert plan_service.trial_status == TrialStatus.NOT_STARTED.value

    def test_plan_service_trial_status_expired(self):
        trial_start_date = datetime.utcnow()
        trial_end_date_expired = trial_start_date - timedelta(days=1)
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date_expired,
            trial_status=TrialStatus.EXPIRED.value,
        )
        plan_service = PlanService(current_org=current_org)

        assert plan_service.trial_status == TrialStatus.EXPIRED.value

    def test_plan_service_trial_status_ongoing(self):
        trial_start_date = datetime.utcnow()
        trial_end_date_ongoing = trial_start_date + timedelta(days=5)
        current_org = OwnerFactory(
            plan=PlanName.TRIAL_PLAN_NAME.value,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date_ongoing,
            trial_status=TrialStatus.ONGOING.value,
        )
        plan_service = PlanService(current_org=current_org)

        assert plan_service.trial_status == TrialStatus.ONGOING.value
        assert plan_service.is_org_trialing == True

    def test_plan_service_expire_trial_when_upgrading_successful_if_trial_is_not_started(
        self,
    ):
        current_org_with_ongoing_trial = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=None,
            trial_end_date=None,
            trial_status=TrialStatus.NOT_STARTED.value,
        )
        plan_service = PlanService(current_org=current_org_with_ongoing_trial)
        plan_service.expire_trial_when_upgrading()
        assert current_org_with_ongoing_trial.trial_status == TrialStatus.EXPIRED.value
        assert current_org_with_ongoing_trial.plan_activated_users is None
        assert current_org_with_ongoing_trial.plan_user_count == 1
        assert current_org_with_ongoing_trial.trial_end_date == datetime.utcnow()

    def test_plan_service_expire_trial_when_upgrading_successful_if_trial_is_ongoing(
        self,
    ):
        trial_start_date = datetime.utcnow()
        trial_end_date_ongoing = trial_start_date + timedelta(days=5)
        current_org_with_ongoing_trial = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date_ongoing,
            trial_status=TrialStatus.ONGOING.value,
        )
        plan_service = PlanService(current_org=current_org_with_ongoing_trial)
        plan_service.expire_trial_when_upgrading()
        assert current_org_with_ongoing_trial.trial_status == TrialStatus.EXPIRED.value
        assert current_org_with_ongoing_trial.plan_activated_users is None
        assert current_org_with_ongoing_trial.plan_user_count == 1
        assert current_org_with_ongoing_trial.trial_end_date == datetime.utcnow()

    def test_plan_service_expire_trial_users_pretrial_users_count_if_existing(
        self,
    ):
        trial_start_date = datetime.utcnow()
        trial_end_date_ongoing = trial_start_date + timedelta(days=5)
        pretrial_users_count = 5
        current_org_with_ongoing_trial = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date_ongoing,
            trial_status=TrialStatus.ONGOING.value,
            pretrial_users_count=pretrial_users_count,
        )
        plan_service = PlanService(current_org=current_org_with_ongoing_trial)
        plan_service.expire_trial_when_upgrading()
        assert current_org_with_ongoing_trial.trial_status == TrialStatus.EXPIRED.value
        assert current_org_with_ongoing_trial.plan_activated_users is None
        assert current_org_with_ongoing_trial.plan_user_count == pretrial_users_count
        assert current_org_with_ongoing_trial.trial_end_date == datetime.utcnow()

    def test_plan_service_start_trial_errors_if_status_is_ongoing(self):
        trial_start_date = datetime.utcnow()
        trial_end_date = trial_start_date + timedelta(
            days=TrialDaysAmount.CODECOV_SENTRY.value
        )
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date,
            trial_status=TrialStatus.ONGOING.value,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        with self.assertRaises(ValidationError):
            plan_service.start_trial(current_owner=current_owner)

    def test_plan_service_start_trial_errors_if_status_is_expired(self):
        trial_start_date = datetime.utcnow()
        trial_end_date = trial_start_date + timedelta(days=-1)
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date,
            trial_status=TrialStatus.EXPIRED.value,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        with self.assertRaises(ValidationError):
            plan_service.start_trial(current_owner=current_owner)

    def test_plan_service_start_trial_errors_if_status_is_cannot_trial(self):
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=None,
            trial_end_date=None,
            trial_status=TrialStatus.CANNOT_TRIAL.value,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        with self.assertRaises(ValidationError):
            plan_service.start_trial(current_owner=current_owner)

    def test_plan_service_start_trial_errors_owners_plan_is_not_a_free_plan(self):
        current_org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            trial_start_date=None,
            trial_end_date=None,
            trial_status=TrialStatus.CANNOT_TRIAL.value,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        with self.assertRaises(ValidationError):
            plan_service.start_trial(current_owner=current_owner)

    def test_plan_service_start_trial_succeeds_if_trial_has_not_started(self):
        trial_start_date = None
        trial_end_date = None
        plan_user_count = 5
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date,
            trial_status=TrialStatus.NOT_STARTED.value,
            plan_user_count=plan_user_count,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        plan_service.start_trial(current_owner=current_owner)
        assert current_org.trial_start_date == datetime.utcnow()
        assert current_org.trial_end_date == datetime.utcnow() + timedelta(
            days=TrialDaysAmount.CODECOV_SENTRY.value
        )
        assert current_org.trial_status == TrialStatus.ONGOING.value
        assert current_org.plan == PlanName.TRIAL_PLAN_NAME.value
        assert current_org.pretrial_users_count == plan_user_count
        assert current_org.plan_user_count == TRIAL_PLAN_SEATS
        assert current_org.plan_auto_activate == True
        assert current_org.trial_fired_by == current_owner.ownerid

    def test_plan_service_start_trial_manually(self):
        trial_start_date = None
        trial_end_date = None
        plan_user_count = 5
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date,
            trial_status=TrialStatus.NOT_STARTED.value,
            plan_user_count=plan_user_count,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        plan_service.start_trial_manually(
            current_owner=current_owner, end_date="2024-01-01 00:00:00"
        )
        assert current_org.trial_start_date == datetime.utcnow()
        assert current_org.trial_end_date == "2024-01-01 00:00:00"
        assert current_org.trial_status == TrialStatus.ONGOING.value
        assert current_org.plan == PlanName.TRIAL_PLAN_NAME.value
        assert current_org.pretrial_users_count == plan_user_count
        assert current_org.plan_user_count == TRIAL_PLAN_SEATS
        assert current_org.plan_auto_activate == True
        assert current_org.trial_fired_by == current_owner.ownerid

    def test_plan_service_start_trial_manually_already_on_paid_plan(self):
        current_org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            trial_start_date=None,
            trial_end_date=None,
            trial_status=TrialStatus.NOT_STARTED.value,
        )
        plan_service = PlanService(current_org=current_org)
        current_owner = OwnerFactory()

        with self.assertRaises(ValidationError):
            plan_service.start_trial_manually(
                current_owner=current_owner, end_date="2024-01-01 00:00:00"
            )

    def test_plan_service_returns_plan_data_for_non_trial_developer_plan(self):
        trial_start_date = None
        trial_end_date = None
        current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date,
        )
        plan_service = PlanService(current_org=current_org)

        developer_plan = FREE_PLAN_REPRESENTATIONS[DEFAULT_FREE_PLAN]
        assert plan_service.current_org == current_org
        assert plan_service.trial_status == TrialStatus.NOT_STARTED.value
        assert plan_service.marketing_name == developer_plan.marketing_name
        assert plan_service.plan_name == developer_plan.value
        assert plan_service.tier_name == developer_plan.tier_name
        assert plan_service.billing_rate == developer_plan.billing_rate
        assert plan_service.base_unit_price == developer_plan.base_unit_price
        assert plan_service.benefits == developer_plan.benefits
        assert (
            plan_service.monthly_uploads_limit == developer_plan.monthly_uploads_limit
        )  # should be 250
        assert plan_service.monthly_uploads_limit == 250

    def test_plan_service_returns_plan_data_for_trialing_user_trial_plan(self):
        trial_start_date = datetime.utcnow()
        trial_end_date = datetime.utcnow() + timedelta(
            days=TrialDaysAmount.CODECOV_SENTRY.value
        )
        current_org = OwnerFactory(
            plan=PlanName.TRIAL_PLAN_NAME.value,
            trial_start_date=trial_start_date,
            trial_end_date=trial_end_date,
            trial_status=TrialStatus.ONGOING.value,
        )
        plan_service = PlanService(current_org=current_org)

        trial_plan = TRIAL_PLAN_REPRESENTATION[PlanName.TRIAL_PLAN_NAME.value]
        assert plan_service.trial_status == TrialStatus.ONGOING.value
        assert plan_service.marketing_name == trial_plan.marketing_name
        assert plan_service.plan_name == trial_plan.value
        assert plan_service.tier_name == trial_plan.tier_name
        assert plan_service.billing_rate == trial_plan.billing_rate
        assert plan_service.base_unit_price == trial_plan.base_unit_price
        assert plan_service.benefits == trial_plan.benefits
        assert plan_service.monthly_uploads_limit is None  # Not 250 since it's trialing

    def test_plan_service_sets_default_plan_data_values_correctly(self):
        current_org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            stripe_subscription_id="test-sub-123",
            plan_user_count=20,
            plan_activated_users=[44],
            plan_auto_activate=False,
        )
        current_org.save()

        plan_service = PlanService(current_org=current_org)
        plan_service.set_default_plan_data()

        assert current_org.plan == DEFAULT_FREE_PLAN
        assert current_org.plan_user_count == 1
        assert current_org.plan_activated_users is None
        assert current_org.stripe_subscription_id is None

    def test_plan_service_returns_if_owner_has_trial_dates(self):
        current_org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            trial_start_date=datetime.utcnow(),
            trial_end_date=datetime.utcnow() + timedelta(days=14),
        )
        current_org.save()

        plan_service = PlanService(current_org=current_org)

        assert plan_service.has_trial_dates == True

    def test_plan_service_gitlab_with_root_org(self):
        root_owner_org = OwnerFactory(
            service=Service.GITLAB.value,
            plan=PlanName.FREE_PLAN_NAME.value,
            plan_user_count=1,
            service_id="1234",
        )
        middle_org = OwnerFactory(
            service=Service.GITLAB.value,
            service_id="5678",
            parent_service_id=root_owner_org.service_id,
        )
        child_owner_org = OwnerFactory(
            service=Service.GITLAB.value,
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            plan_user_count=20,
            parent_service_id=middle_org.service_id,
        )
        # root_plan and child_plan should be the same
        root_plan = PlanService(current_org=root_owner_org)
        child_plan = PlanService(current_org=child_owner_org)

        assert root_plan.is_pro_plan == child_plan.is_pro_plan == False
        assert root_plan.plan_user_count == child_plan.plan_user_count == 1
        assert (
            root_plan.plan_name == child_plan.plan_name == PlanName.FREE_PLAN_NAME.value
        )

    def test_plan_service_activated_user_count_includes_student_users(self):
        student_user = OwnerFactory(student=True)
        other_user = OwnerFactory()
        current_org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            plan_activated_users=[student_user.ownerid, other_user.ownerid],
            plan_auto_activate=False,
            plan_user_count=2,
        )
        current_org.save()

        plan = PlanService(current_org=current_org)

        assert plan.has_seats_left == True

    def test_plan_service_activated_user_count_includes_student_users_and_has_no_seats_left(
        self,
    ):
        student_user = OwnerFactory(student=True)
        other_user = OwnerFactory()
        other_user_2 = OwnerFactory()
        current_org = OwnerFactory(
            plan=PlanName.CODECOV_PRO_MONTHLY.value,
            plan_activated_users=[
                student_user.ownerid,
                other_user.ownerid,
                other_user_2.ownerid,
            ],
            plan_auto_activate=False,
            plan_user_count=2,
        )
        current_org.save()

        plan = PlanService(current_org=current_org)

        assert plan.has_seats_left == False


class AvailablePlansBeforeTrial(TestCase):
    """
    - DEFAULT_FREE_PLAN, no trial -> users-pr-inappm/y, DEFAULT_FREE_PLAN
    - users-free, no trial -> users-pr-inappm/y, DEFAULT_FREE_PLAN, users-free
    - users-teamm/y, no trial -> users-pr-inappm/y, DEFAULT_FREE_PLAN, users-teamm/y
    - users-pr-inappm/y, no trial -> users-pr-inappm/y,  DEFAULT_FREE_PLAN
    - sentry customer, DEFAULT_FREE_PLAN, no trial -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN
    - sentry customer, users-teamm/y, no trial -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN, users-teamm/y
    - sentry customer, users-sentrym/y, no trial -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_all_plans_and_tiers()

    def setUp(self):
        self.current_org = OwnerFactory(
            trial_start_date=None,
            trial_end_date=None,
            trial_status=TrialStatus.NOT_STARTED.value,
        )
        self.owner = OwnerFactory()

    def test_available_plans_for_developer_plan_non_trial(
        self,
    ):
        self.current_org.plan = DEFAULT_FREE_PLAN
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    def test_available_plans_for_free_plan_non_trial(
        self,
    ):
        self.current_org.plan = PlanName.FREE_PLAN_NAME.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.FREE_PLAN_NAME.value,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    def test_available_plans_for_team_plan_non_trial(
        self,
    ):
        self.current_org.plan = PlanName.TEAM_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    def test_available_plans_for_pro_plan_non_trial(self):
        self.current_org.plan = PlanName.CODECOV_PRO_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_customer_developer_plan_non_trial(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = DEFAULT_FREE_PLAN
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_customer_team_plan_non_trial(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = PlanName.TEAM_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }
        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_plan_non_trial(self, is_sentry_user):
        is_sentry_user.return_value = True
        self.current_org.plan = PlanName.SENTRY_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )


@freeze_time("2023-06-19")
class AvailablePlansExpiredTrialLessThanTenUsers(TestCase):
    """
    - {DEFAULT_FREE_PLAN}, has trialed, less than 10 users -> users-pr-inappm/y, DEFAULT_FREE_PLAN, users-teamm/y
    - users-teamm/y, has trialed, less than 10 users -> users-pr-inappm/y, DEFAULT_FREE_PLAN, users-teamm/y
    - users-pr-inappm/y, has trialed, less than 10 users -> users-pr-inappm/y, DEFAULT_FREE_PLAN, users-teamm/y
    - sentry customer, DEFAULT_FREE_PLAN, has trialed, less than 10 users -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN, users-teamm/y
    - sentry customer, users-teamm/y, has trialed, less than 10 users -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN, users-teamm/y
    - sentry customer, users-sentrym/y, has trialed, less than 10 users -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN, users-teamm/y
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_all_plans_and_tiers()

    def setUp(self):
        self.current_org = OwnerFactory(
            trial_start_date=datetime.utcnow() + timedelta(days=-10),
            trial_end_date=datetime.utcnow() + timedelta(days=-3),
            trial_status=TrialStatus.EXPIRED.value,
            plan_user_count=3,
        )
        self.owner = OwnerFactory()

    def test_available_plans_for_developer_plan_expired_trial_less_than_10_users(
        self,
    ):
        self.current_org.plan = DEFAULT_FREE_PLAN
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }
        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    def test_available_plans_for_team_plan_expired_trial_less_than_10_users(
        self,
    ):
        self.current_org.plan = PlanName.TEAM_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }
        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    def test_available_plans_for_pro_plan_expired_trial_less_than_10_users(self):
        self.current_org.plan = PlanName.CODECOV_PRO_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_customer_developer_plan_expired_trial_less_than_10_users(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = DEFAULT_FREE_PLAN
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_customer_team_plan_expired_trial_less_than_10_users(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = PlanName.TEAM_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)
        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_plan_expired_trial_less_than_10_users(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = PlanName.SENTRY_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )


@freeze_time("2023-06-19")
class AvailablePlansExpiredTrialMoreThanTenActivatedUsers(TestCase):
    """
    - users-pr-inappm/y, has trialed, more than 10 activated users -> users-pr-inappm/y, DEFAULT_FREE_PLAN
    - sentry customer, DEFAULT_FREE_PLAN, has trialed, more than 10 activated users -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN
    - sentry customer, users-sentrym/y, has trialed, more than 10 activated users -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_all_plans_and_tiers()

    def setUp(self):
        self.current_org = OwnerFactory(
            trial_start_date=datetime.utcnow() + timedelta(days=-10),
            trial_end_date=datetime.utcnow() + timedelta(days=-3),
            trial_status=TrialStatus.EXPIRED.value,
            plan_user_count=1,
            plan_activated_users=[i for i in range(13)],
        )
        self.owner = OwnerFactory()

    def test_available_plans_for_pro_plan_expired_trial_more_than_10_users(self):
        self.current_org.plan = PlanName.CODECOV_PRO_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_customer_developer_plan_expired_trial_more_than_10_users(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = DEFAULT_FREE_PLAN
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
        }
        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_available_plans_for_sentry_plan_expired_trial_more_than_10_users(
        self, is_sentry_user
    ):
        is_sentry_user.return_value = True
        self.current_org.plan = PlanName.SENTRY_MONTHLY.value
        self.current_org.save()

        plan_service = PlanService(current_org=self.current_org)

        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
        }

        assert (
            set(
                plan["value"] for plan in plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )


@freeze_time("2023-06-19")
class AvailablePlansExpiredTrialMoreThanTenSeatsLessThanTenActivatedUsers(TestCase):
    """
    Tests that what matters for Team plan is activated users not the total seat count
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_all_plans_and_tiers()

    def setUp(self):
        self.expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

    def test_currently_team_plan(self):
        self.current_org = OwnerFactory(
            plan_user_count=100,
            plan_activated_users=[i for i in range(10)],
            plan=PlanName.TEAM_MONTHLY.value,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == self.expected_result
        )

    def test_trial_expired(self):
        self.current_org = OwnerFactory(
            plan_user_count=100,
            plan_activated_users=[i for i in range(10)],
            trial_status=TrialStatus.EXPIRED.value,
            trial_start_date=datetime.utcnow() + timedelta(days=-10),
            trial_end_date=datetime.utcnow() + timedelta(days=-3),
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == self.expected_result
        )

    def test_trial_ongoing(self):
        self.current_org = OwnerFactory(
            plan_user_count=100,
            plan_activated_users=[i for i in range(10)],
            trial_status=TrialStatus.ONGOING.value,
            trial_start_date=datetime.utcnow() + timedelta(days=-10),
            trial_end_date=datetime.utcnow() + timedelta(days=3),
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == self.expected_result
        )

    def test_trial_not_started(self):
        self.current_org = OwnerFactory(
            plan_user_count=100,
            plan_activated_users=[i for i in range(10)],
            trial_status=TrialStatus.NOT_STARTED.value,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        self.expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == self.expected_result
        )


@freeze_time("2023-06-19")
class AvailablePlansOngoingTrial(TestCase):
    """
    Non Sentry User is trialing
        when <=10 activated seats -> users-pr-inappm/y, DEFAULT_FREE_PLAN, users-teamm/y
        when > 10 activated seats -> users-pr-inappm/y, DEFAULT_FREE_PLAN
    Sentry User is trialing
        when <=10 activated seats -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN, users-teamm/y
        when > 10 activated seats -> users-pr-inappm/y, users-sentrym/y, DEFAULT_FREE_PLAN
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_all_plans_and_tiers()

    def setUp(self):
        self.current_org = OwnerFactory(
            plan=DEFAULT_FREE_PLAN,
            trial_start_date=datetime.utcnow(),
            trial_end_date=datetime.utcnow() + timedelta(days=14),
            trial_status=TrialStatus.ONGOING.value,
            plan_user_count=1000,
            plan_activated_users=None,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

    def test_non_sentry_user(self):
        # [Developer, Pro Monthly, Pro Yearly, Team Monthly, Team Yearly]
        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }

        # Can do Team plan when plan_activated_users is null
        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

        self.current_org.plan_activated_users = [i for i in range(10)]
        self.current_org.save()

        # Can do Team plan when at 10 activated users
        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

        self.current_org.plan_activated_users = [i for i in range(11)]
        self.current_org.save()

        # [Developer, Pro Monthly, Pro Yearly]
        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.CODECOV_PRO_MONTHLY.value,
        }

        # Can not do Team plan when at 11 activated users
        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

    @patch("shared.plan.service.is_sentry_user")
    def test_sentry_user(self, is_sentry_user):
        self.current_org.plan = PlanName.SENTRY_MONTHLY.value
        self.current_org.save()

        is_sentry_user.return_value = True

        # [Developer, Pro Monthly, Pro Yearly, Sentry Monthly, Sentry Yearly, Team Monthly, Team Yearly]
        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
            PlanName.TEAM_MONTHLY.value,
            PlanName.TEAM_YEARLY.value,
        }
        # Can do Team plan when plan_activated_users is null
        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

        self.current_org.plan_activated_users = [i for i in range(10)]
        self.current_org.save()

        # Can do Team plan when at 10 activated users
        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )

        self.current_org.plan_activated_users = [i for i in range(11)]
        self.current_org.save()

        # [Developer, Pro Monthly, Pro Yearly, Sentry Monthly, Sentry Yearly]
        expected_result = {
            DEFAULT_FREE_PLAN,
            PlanName.CODECOV_PRO_YEARLY.value,
            PlanName.CODECOV_PRO_MONTHLY.value,
            PlanName.SENTRY_MONTHLY.value,
            PlanName.SENTRY_YEARLY.value,
        }

        # Can not do Team plan when at 11 activated users
        assert (
            set(
                plan["value"]
                for plan in self.plan_service.available_plans(owner=self.owner)
            )
            == expected_result
        )


@override_settings(IS_ENTERPRISE=False)
class PlanServiceIs___PlanTests(TestCase):
    def test_is_trial_plan(self):
        tier = TierFactory(tier_name=TierName.TRIAL.value)
        plan = PlanFactory(
            tier=tier,
            name=PlanName.TRIAL_PLAN_NAME.value,
            paid_plan=False,
        )
        self.current_org = OwnerFactory(
            plan=plan.name,
            trial_start_date=datetime.utcnow(),
            trial_end_date=datetime.utcnow() + timedelta(days=14),
            trial_status=TrialStatus.ONGOING.value,
            plan_user_count=1000,
            plan_activated_users=None,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert self.plan_service.is_trial_plan == True
        assert self.plan_service.is_sentry_plan == False
        assert self.plan_service.is_team_plan == False
        assert self.plan_service.is_free_plan == False
        assert self.plan_service.is_pro_plan == False
        assert self.plan_service.is_enterprise_plan == False
        assert self.plan_service.is_pr_billing_plan == True

    def test_is_team_plan(self):
        tier = TierFactory(tier_name=TierName.TEAM.value)
        plan = PlanFactory(
            tier=tier,
            name=PlanName.TEAM_MONTHLY.value,
            paid_plan=True,
        )
        self.current_org = OwnerFactory(
            plan=plan.name,
            trial_status=TrialStatus.EXPIRED.value,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert self.plan_service.is_trial_plan == False
        assert self.plan_service.is_sentry_plan == False
        assert self.plan_service.is_team_plan == True
        assert self.plan_service.is_free_plan == False
        assert self.plan_service.is_pro_plan == False
        assert self.plan_service.is_enterprise_plan == False
        assert self.plan_service.is_pr_billing_plan == True

    def test_is_sentry_plan(self):
        tier = TierFactory(tier_name=TierName.SENTRY.value)
        plan = PlanFactory(
            tier=tier,
            name=PlanName.SENTRY_MONTHLY.value,
            paid_plan=True,
        )
        self.current_org = OwnerFactory(
            plan=plan.name,
            trial_status=TrialStatus.EXPIRED.value,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert self.plan_service.is_trial_plan == False
        assert self.plan_service.is_sentry_plan == True
        assert self.plan_service.is_team_plan == False
        assert self.plan_service.is_free_plan == False
        assert self.plan_service.is_pro_plan == True
        assert self.plan_service.is_enterprise_plan == False
        assert self.plan_service.is_pr_billing_plan == True

    def test_is_free_plan(self):
        tier = TierFactory(tier_name=TierName.BASIC.value)
        plan = PlanFactory(
            tier=tier,
            name=PlanName.FREE_PLAN_NAME.value,
            paid_plan=False,
        )
        self.current_org = OwnerFactory(
            plan=plan.name,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert self.plan_service.is_trial_plan == False
        assert self.plan_service.is_sentry_plan == False
        assert self.plan_service.is_team_plan == False
        assert self.plan_service.is_free_plan == True
        assert self.plan_service.is_pro_plan == False
        assert self.plan_service.is_enterprise_plan == False
        assert self.plan_service.is_pr_billing_plan == True

    def test_is_pro_plan(self):
        tier = TierFactory(tier_name=TierName.PRO.value)
        plan = PlanFactory(
            tier=tier,
            name=PlanName.CODECOV_PRO_MONTHLY.value,
            paid_plan=True,
        )

        self.current_org = OwnerFactory(
            plan=plan.name,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert self.plan_service.is_trial_plan == False
        assert self.plan_service.is_sentry_plan == False
        assert self.plan_service.is_team_plan == False
        assert self.plan_service.is_free_plan == False
        assert self.plan_service.is_pro_plan == True
        assert self.plan_service.is_enterprise_plan == False
        assert self.plan_service.is_pr_billing_plan == True

    def test_is_enterprise_plan(self):
        tier = TierFactory(tier_name=TierName.ENTERPRISE.value)
        plan = PlanFactory(
            tier=tier,
            name=PlanName.ENTERPRISE_CLOUD_YEARLY.value,
            paid_plan=True,
        )
        self.current_org = OwnerFactory(
            plan=plan.name,
        )
        self.owner = OwnerFactory()
        self.plan_service = PlanService(current_org=self.current_org)

        assert self.plan_service.is_trial_plan == False
        assert self.plan_service.is_sentry_plan == False
        assert self.plan_service.is_team_plan == False
        assert self.plan_service.is_free_plan == False
        assert self.plan_service.is_pro_plan == False
        assert self.plan_service.is_enterprise_plan == True
        assert self.plan_service.is_pr_billing_plan == True
