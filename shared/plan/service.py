import logging
from datetime import datetime, timedelta
from functools import cached_property
from typing import List, Optional

from shared.billing import is_pr_billing_plan
from shared.config import get_config
from shared.django_apps.codecov.commands.exceptions import ValidationError
from shared.django_apps.codecov_auth.models import Owner, Plan, Service
from shared.plan.constants import (
    DEFAULT_FREE_PLAN,
    TEAM_PLAN_MAX_USERS,
    TRIAL_PLAN_SEATS,
    PlanBillingRate,
    PlanName,
    TierName,
    TrialDaysAmount,
    TrialStatus,
)
from shared.self_hosted.service import enterprise_has_seats_left, license_seats

log = logging.getLogger(__name__)


# This originally belongs to the sentry service in API but this is a temporary fn to avoid importing the whole service
def is_sentry_user(owner: Owner) -> bool:
    """Returns true if the given owner has been linked with a Sentry user."""
    return owner.sentry_user_id is not None


# TODO: Consider moving some of these methods to the billing directory as they overlap billing functionality
class PlanService:
    def __init__(self, current_org: Owner):
        """
        Initializes a PlanService object for a specific organization.

        Args:
            current_org (Owner): The organization for which the plan service is being initialized.

        Raises:
            ValueError: If the organization's plan is unsupported.
        """
        if (
            current_org.service == Service.GITLAB.value
            and current_org.parent_service_id
        ):
            # for GitLab groups and subgroups, use the plan on the root org
            self.current_org = current_org.root_organization
        else:
            self.current_org = current_org

        if not Plan.objects.filter(name=self.current_org.plan).exists():
            raise ValueError("Unsupported plan")
        self._plan_data = None

    def update_plan(self, name: str, user_count: Optional[int]) -> None:
        """Updates the organization's plan and user count."""
        if not Plan.objects.filter(name=name).exists():
            raise ValueError("Unsupported plan")
        if not user_count:
            raise ValueError("Quantity Needed")
        self.current_org.plan = name
        self.current_org.plan_user_count = user_count
        self._plan_data = Plan.objects.select_related("tier").get(name=name)
        self.current_org.delinquent = False
        self.current_org.save()

    def current_org(self) -> Owner:
        return self.current_org

    def set_default_plan_data(self) -> None:
        """Sets the organization to the default developer plan."""
        log.info(
            f"Setting plan to {DEFAULT_FREE_PLAN} for owner {self.current_org.ownerid}"
        )
        self.current_org.plan = DEFAULT_FREE_PLAN
        self.current_org.plan_activated_users = None
        self.current_org.plan_user_count = 1
        self.current_org.stripe_subscription_id = None
        self.current_org.save()

    @property
    def has_account(self) -> bool:
        """Returns whether the organization has an associated account."""
        return self.current_org.account is not None

    @cached_property
    def plan_data(self) -> Plan:
        """Returns the plan data for the organization, either from account or default."""
        if self._plan_data is None:
            self._plan_data = Plan.objects.select_related("tier").get(
                name=self.current_org.account.plan
                if self.has_account
                else self.current_org.plan
            )
        return self._plan_data

    @property
    def plan_name(self) -> str:
        """Returns the name of the organization's current plan."""
        return self.plan_data.name

    @property
    def plan_user_count(self) -> int:
        """Returns the number of users allowed by the organization's plan."""
        if get_config("setup", "enterprise_license"):
            return license_seats()
        if self.has_account:
            return self.current_org.account.total_seat_count
        return self.current_org.plan_user_count

    @property
    def plan_activated_users(self) -> Optional[List[int]]:
        """Returns the list of activated users for the plan."""
        return self.current_org.plan_activated_users

    @property
    def pretrial_users_count(self) -> int:
        """Returns the number of pretrial users."""
        return self.current_org.pretrial_users_count or 1

    @property
    def marketing_name(self) -> str:
        """Returns the marketing name of the plan."""
        return self.plan_data.marketing_name

    @property
    def billing_rate(self) -> Optional[PlanBillingRate]:
        """Returns the billing rate for the plan."""
        return self.plan_data.billing_rate

    @property
    def base_unit_price(self) -> int:
        """Returns the base unit price for the plan."""
        return self.plan_data.base_unit_price

    @property
    def benefits(self) -> List[str]:
        """Returns the benefits associated with the plan."""
        return self.plan_data.benefits

    @property
    def monthly_uploads_limit(self) -> Optional[int]:
        """
        Property that returns monthly uploads limit based on your trial status

        Returns:
            Optional number of monthly uploads
        """
        return self.plan_data.monthly_uploads_limit

    @property
    def tier_name(self) -> TierName:
        """Returns the tier name of the plan."""
        return self.plan_data.tier.tier_name

    def available_plans(self, owner: Owner) -> List[Plan]:
        """Returns the available plans for the owner and organization."""
        available_plans = {
            Plan.objects.select_related("tier").get(name=DEFAULT_FREE_PLAN)
        }
        curr_plan = self.plan_data
        if not curr_plan.paid_plan:
            available_plans.add(curr_plan)

        # Build list of available tiers based on conditions
        available_tiers = [TierName.PRO.value]

        if is_sentry_user(owner):
            available_tiers.append(TierName.SENTRY.value)

        if (
            not self.plan_activated_users
            or len(self.plan_activated_users) <= TEAM_PLAN_MAX_USERS
        ):
            available_tiers.append(TierName.TEAM.value)

        available_plans.update(
            Plan.objects.select_related("tier").filter(
                tier__tier_name__in=available_tiers, is_active=True
            )
        )

        return list(available_plans)

    def _start_trial_helper(
        self,
        current_owner: Owner,
        end_date: Optional[datetime] = None,
        is_extension: bool = False,
    ) -> None:
        """Helper method to start or extend a trial for the organization."""
        start_date = datetime.now()

        if not is_extension:
            self.current_org.trial_start_date = start_date
            self.current_org.trial_status = TrialStatus.ONGOING.value
            self.current_org.plan = PlanName.TRIAL_PLAN_NAME.value
            self.current_org.pretrial_users_count = self.current_org.plan_user_count
            self.current_org.plan_user_count = TRIAL_PLAN_SEATS
            self.current_org.plan_auto_activate = True

        self.current_org.trial_end_date = (
            end_date
            if end_date
            else start_date + timedelta(days=TrialDaysAmount.CODECOV_SENTRY.value)
        )
        self.current_org.trial_fired_by = current_owner.ownerid
        self.current_org.save()

    # Trial Data
    def start_trial(self, current_owner: Owner) -> None:
        """
        Method that starts trial on an organization if the trial_start_date
        is not empty.

        Returns:
            No value

        Raises:
            ValidationError: if trial has already started
        """
        if self.trial_status != TrialStatus.NOT_STARTED.value:
            raise ValidationError("Cannot start an existing trial")
        if not Plan.objects.filter(name=self.plan_name, paid_plan=False).exists():
            raise ValidationError("Cannot trial from a paid plan")

        self._start_trial_helper(current_owner)

    def start_trial_manually(self, current_owner: Owner, end_date: datetime) -> None:
        """
        Method that start trial immediately and ends at a predefined date for an organization
        Used by administrators to manually start and extend trials

        Returns:
            No value
        """
        # Start a new trial plan for free users currently not on trial

        if self.plan_data.tier.tier_name == TierName.TRIAL.value:
            self._start_trial_helper(current_owner, end_date, is_extension=True)
        elif self.plan_data.paid_plan is False:
            self._start_trial_helper(current_owner, end_date, is_extension=False)
        # Extend an existing trial plan for users currently on trial
        else:
            raise ValidationError("Cannot trial from a paid plan")

    def cancel_trial(self) -> None:
        """Cancels the ongoing trial for the organization."""
        if not self.is_org_trialing:
            raise ValidationError("Cannot cancel a trial that is not ongoing")
        now = datetime.now()
        self.current_org.trial_status = TrialStatus.EXPIRED.value
        self.current_org.trial_end_date = now
        self.set_default_plan_data()

    def expire_trial_when_upgrading(self) -> None:
        """
        Method that expires trial on an organization based on it's current trial status.


        Returns:
            No value
        """
        if self.trial_status == TrialStatus.EXPIRED.value:
            return
        if self.trial_status != TrialStatus.CANNOT_TRIAL.value:
            # Not adjusting the trial start/end dates here as some customers can
            # directly purchase a plan without trialing first
            self.current_org.trial_status = TrialStatus.EXPIRED.value
            self.current_org.plan_activated_users = None
            self.current_org.plan_user_count = (
                self.current_org.pretrial_users_count or 1
            )
            self.current_org.trial_end_date = datetime.now()

            self.current_org.save()

    @property
    def trial_status(self) -> TrialStatus:
        """Returns the trial status of the organization."""
        return self.current_org.trial_status

    @property
    def trial_start_date(self) -> Optional[datetime]:
        """Returns the trial start date."""
        return self.current_org.trial_start_date

    @property
    def trial_end_date(self) -> Optional[datetime]:
        """Returns the trial end date."""
        return self.current_org.trial_end_date

    @property
    def trial_total_days(self) -> Optional[TrialDaysAmount]:
        """Returns the total number of trial days."""
        return TrialDaysAmount.CODECOV_SENTRY.value

    @property
    def is_org_trialing(self) -> bool:
        return (
            self.trial_status == TrialStatus.ONGOING.value
            and self.plan_name == PlanName.TRIAL_PLAN_NAME.value
        )

    @property
    def has_trial_dates(self) -> bool:
        return bool(self.trial_start_date and self.trial_end_date)

    @property
    def has_seats_left(self) -> bool:
        if get_config("setup", "enterprise_license"):
            return enterprise_has_seats_left()
        if self.has_account:
            # edge case: IF the User is already a plan_activated_user on any of the Orgs in the Account,
            # AND their Account is at capacity,
            # AND they try to become a plan_activated_user on another Org in the Account,
            # has_seats_left will evaluate as False even though the User should be allowed to activate on the Org.
            return self.current_org.account.can_activate_user()
        return (
            self.current_org.activated_user_count is None
            or self.current_org.activated_user_count < self.plan_user_count
        )

    @property
    def is_enterprise_plan(self) -> bool:
        return self.plan_data.is_enterprise_plan

    @property
    def is_free_plan(self) -> bool:
        return self.plan_data.is_free_plan and not self.is_org_trialing

    @property
    def is_pro_plan(self) -> bool:
        return self.plan_data.is_pro_plan

    @property
    def is_sentry_plan(self) -> bool:
        return self.plan_data.is_sentry_plan

    @property
    def is_team_plan(self) -> bool:
        return self.plan_data.is_team_plan

    @property
    def is_trial_plan(self) -> bool:
        return self.plan_data.is_trial_plan

    @property
    def is_pr_billing_plan(self) -> bool:
        return is_pr_billing_plan(plan=self.plan_name)
