from enum import Enum

from django.conf import settings
from typing_extensions import deprecated

from shared.license import get_current_license
from shared.plan.constants import PlanName


@deprecated("Use PlanService")
class BillingPlan(Enum):
    users_basic = PlanName.BASIC_PLAN_NAME.value
    users_trial = PlanName.TRIAL_PLAN_NAME.value
    pr_monthly = PlanName.CODECOV_PRO_MONTHLY.value
    pr_yearly = PlanName.CODECOV_PRO_YEARLY.value
    SENTRY_MONTHLY = PlanName.SENTRY_MONTHLY.value
    SENTRY_YEARLY = PlanName.SENTRY_YEARLY.value
    team_monthly = PlanName.TEAM_MONTHLY.value
    team_yearly = PlanName.TEAM_YEARLY.value
    users_ghm = PlanName.GHM_PLAN_NAME.value
    users_free = PlanName.FREE_PLAN_NAME.value
    users_monthly = PlanName.CODECOV_PRO_MONTHLY_LEGACY.value
    users_yearly = PlanName.CODECOV_PRO_YEARLY_LEGACY.value
    enterprise_cloud_monthly = PlanName.ENTERPRISE_CLOUD_MONTHLY.value
    enterprise_cloud_yearly = PlanName.ENTERPRISE_CLOUD_YEARLY.value

    def __init__(self, db_name):
        self.db_name = db_name

    @classmethod
    def from_str(cls, plan_name: str):
        for plan in cls:
            if plan.db_name == plan_name:
                return plan


@deprecated("use is_enterprise_plan() in PlanService")
def is_enterprise_cloud_plan(plan: BillingPlan) -> bool:
    return plan in [
        BillingPlan.enterprise_cloud_monthly,
        BillingPlan.enterprise_cloud_yearly,
    ]


@deprecated("use is_pr_billing_plan() in PlanService")
def is_pr_billing_plan(plan: str) -> bool:
    if not settings.IS_ENTERPRISE:
        return plan not in [
            PlanName.CODECOV_PRO_MONTHLY_LEGACY.value,
            PlanName.CODECOV_PRO_YEARLY_LEGACY.value,
        ]
    else:
        return get_current_license().is_pr_billing
