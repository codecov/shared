import enum
from dataclasses import dataclass
from typing import List, Optional

from shared.django_apps.utils.config import RUN_ENV


class MonthlyUploadLimits(enum.Enum):
    CODECOV_FREE_PLAN = 250
    CODECOV_TEAM_PLAN = 2500


class TrialDaysAmount(enum.Enum):
    CODECOV_SENTRY = 14


class PlanMarketingName(enum.Enum):
    CODECOV_PRO = "Pro"
    SENTRY_PRO = "Sentry Pro"
    ENTERPRISE_CLOUD = "Enterprise Cloud"
    GITHUB_MARKETPLACE = "Github Marketplace"
    FREE = "Developer"
    BASIC = "Developer"
    TRIAL = "Developer"
    TEAM = "Team"


DEFAULT_FREE_PLAN = "users-pr-inappy" if RUN_ENV == "ENTERPRISE" else "users-developer"


class PlanName(enum.Enum):
    # If you add or remove, make a migration for Account table
    BASIC_PLAN_NAME = "users-basic"
    TRIAL_PLAN_NAME = "users-trial"
    CODECOV_PRO_MONTHLY = "users-pr-inappm"
    CODECOV_PRO_YEARLY = "users-pr-inappy"
    SENTRY_MONTHLY = "users-sentrym"
    SENTRY_YEARLY = "users-sentryy"
    TEAM_MONTHLY = "users-teamm"
    TEAM_YEARLY = "users-teamy"
    GHM_PLAN_NAME = "users"
    FREE_PLAN_NAME = "users-free"
    CODECOV_PRO_MONTHLY_LEGACY = "users-inappm"
    CODECOV_PRO_YEARLY_LEGACY = "users-inappy"
    ENTERPRISE_CLOUD_MONTHLY = "users-enterprisem"
    ENTERPRISE_CLOUD_YEARLY = "users-enterprisey"
    USERS_DEVELOPER = "users-developer"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class PlanBillingRate(enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "annually"


class PlanPrice(enum.Enum):
    MONTHLY = 12
    YEARLY = 10
    CODECOV_FREE = 0
    CODECOV_BASIC = 0
    CODECOV_TRIAL = 0
    TEAM_MONTHLY = 5
    TEAM_YEARLY = 4
    GHM_PRICE = 12


class TrialStatus(enum.Enum):
    NOT_STARTED = "not_started"
    ONGOING = "ongoing"
    EXPIRED = "expired"
    CANNOT_TRIAL = "cannot_trial"


class TierName(enum.Enum):
    BASIC = "basic"
    TEAM = "team"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    SENTRY = "sentry"
    TRIAL = "trial"


def convert_to_DTO(plan) -> dict:
    return {
        "marketing_name": plan.marketing_name,
        "value": plan.name,
        "billing_rate": plan.billing_rate,
        "base_unit_price": plan.base_unit_price,
        "benefits": plan.benefits,
        "tier_name": plan.tier.tier_name,
        "monthly_uploads_limit": plan.monthly_uploads_limit,
        "is_free_plan": not plan.paid_plan,
        "is_pro_plan": plan.tier.tier_name == TierName.PRO.value,
        "is_team_plan": plan.tier.tier_name == TierName.TEAM.value,
        "is_enterprise_plan": plan.tier.tier_name == TierName.ENTERPRISE.value,
        "is_trial_plan": plan.tier.tier_name == TierName.TRIAL.value,
        "is_sentry_plan": plan.tier.tier_name == TierName.SENTRY.value,
    }


@dataclass(repr=False)
class PlanData:
    """
    Dataclass that represents plan related information
    """

    marketing_name: PlanMarketingName
    value: PlanName
    billing_rate: Optional[PlanBillingRate]
    base_unit_price: PlanPrice
    benefits: List[str]
    tier_name: TierName
    monthly_uploads_limit: Optional[MonthlyUploadLimits]
    trial_days: Optional[TrialDaysAmount]

    def convert_to_DTO(self) -> dict:
        return {
            "marketing_name": self.marketing_name,
            "value": self.value,
            "billing_rate": self.billing_rate,
            "base_unit_price": self.base_unit_price,
            "benefits": self.benefits,
            "tier_name": self.tier_name,
            "monthly_uploads_limit": self.monthly_uploads_limit,
            "is_free_plan": self.tier_name == TierName.BASIC.value,
            "is_pro_plan": self.tier_name == TierName.PRO.value,
            "is_team_plan": self.tier_name == TierName.TEAM.value,
            "is_enterprise_plan": self.tier_name == TierName.ENTERPRISE.value,
            "is_trial_plan": self.value == PlanName.TRIAL_PLAN_NAME.value,
            "is_sentry_plan": self.value in SENTRY_PAID_USER_PLAN_REPRESENTATIONS,
        }


NON_PR_AUTHOR_PAID_USER_PLAN_REPRESENTATIONS = {
    PlanName.CODECOV_PRO_MONTHLY_LEGACY.value: PlanData(
        marketing_name=PlanMarketingName.CODECOV_PRO.value,
        value=PlanName.CODECOV_PRO_MONTHLY_LEGACY.value,
        billing_rate=PlanBillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.PRO.value,
        monthly_uploads_limit=None,
        trial_days=None,
    ),
    PlanName.CODECOV_PRO_YEARLY_LEGACY.value: PlanData(
        marketing_name=PlanMarketingName.CODECOV_PRO.value,
        value=PlanName.CODECOV_PRO_YEARLY_LEGACY.value,
        billing_rate=PlanBillingRate.YEARLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.PRO.value,
        monthly_uploads_limit=None,
        trial_days=None,
    ),
}


PR_AUTHOR_PAID_USER_PLAN_REPRESENTATIONS = {
    PlanName.CODECOV_PRO_MONTHLY.value: PlanData(
        marketing_name=PlanMarketingName.CODECOV_PRO.value,
        value=PlanName.CODECOV_PRO_MONTHLY.value,
        billing_rate=PlanBillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.PRO.value,
        monthly_uploads_limit=None,
        trial_days=None,
    ),
    PlanName.CODECOV_PRO_YEARLY.value: PlanData(
        marketing_name=PlanMarketingName.CODECOV_PRO.value,
        value=PlanName.CODECOV_PRO_YEARLY.value,
        billing_rate=PlanBillingRate.YEARLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.PRO.value,
        monthly_uploads_limit=None,
        trial_days=None,
    ),
}

SENTRY_PAID_USER_PLAN_REPRESENTATIONS = {
    PlanName.SENTRY_MONTHLY.value: PlanData(
        marketing_name=PlanMarketingName.SENTRY_PRO.value,
        value=PlanName.SENTRY_MONTHLY.value,
        billing_rate=PlanBillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        benefits=[
            "Includes 5 seats",
            "$12 per additional seat",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.SENTRY.value,
        trial_days=TrialDaysAmount.CODECOV_SENTRY.value,
        monthly_uploads_limit=None,
    ),
    PlanName.SENTRY_YEARLY.value: PlanData(
        marketing_name=PlanMarketingName.SENTRY_PRO.value,
        value=PlanName.SENTRY_YEARLY.value,
        billing_rate=PlanBillingRate.YEARLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        benefits=[
            "Includes 5 seats",
            "$10 per additional seat",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.SENTRY.value,
        trial_days=TrialDaysAmount.CODECOV_SENTRY.value,
        monthly_uploads_limit=None,
    ),
}

# TODO: Update these values
ENTERPRISE_CLOUD_USER_PLAN_REPRESENTATIONS = {
    PlanName.ENTERPRISE_CLOUD_MONTHLY.value: PlanData(
        marketing_name=PlanMarketingName.ENTERPRISE_CLOUD.value,
        value=PlanName.ENTERPRISE_CLOUD_MONTHLY.value,
        billing_rate=PlanBillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.ENTERPRISE.value,
        trial_days=None,
        monthly_uploads_limit=None,
    ),
    PlanName.ENTERPRISE_CLOUD_YEARLY.value: PlanData(
        marketing_name=PlanMarketingName.ENTERPRISE_CLOUD.value,
        value=PlanName.ENTERPRISE_CLOUD_YEARLY.value,
        billing_rate=PlanBillingRate.YEARLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.ENTERPRISE.value,
        trial_days=None,
        monthly_uploads_limit=None,
    ),
}

GHM_PLAN_REPRESENTATION = {
    PlanName.GHM_PLAN_NAME.value: PlanData(
        marketing_name=PlanMarketingName.GITHUB_MARKETPLACE.value,
        value=PlanName.GHM_PLAN_NAME.value,
        billing_rate=None,
        base_unit_price=PlanPrice.GHM_PRICE.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
        ],
        tier_name=TierName.PRO.value,
        trial_days=None,
        monthly_uploads_limit=None,
    )
}

BASIC_PLAN = PlanData(
    marketing_name=PlanMarketingName.BASIC.value,
    value=PlanName.BASIC_PLAN_NAME.value,
    billing_rate=None,
    base_unit_price=PlanPrice.CODECOV_BASIC.value,
    benefits=[
        "Up to 1 user",
        "Unlimited public repositories",
        "Unlimited private repositories",
    ],
    tier_name=TierName.BASIC.value,
    monthly_uploads_limit=MonthlyUploadLimits.CODECOV_FREE_PLAN.value,
    trial_days=None,
)

FREE_PLAN = PlanData(
    marketing_name=PlanMarketingName.FREE.value,
    value=PlanName.FREE_PLAN_NAME.value,
    billing_rate=None,
    base_unit_price=PlanPrice.CODECOV_FREE.value,
    benefits=[
        "Up to 1 user",
        "Unlimited public repositories",
        "Unlimited private repositories",
    ],
    tier_name=TierName.BASIC.value,
    trial_days=None,
    monthly_uploads_limit=None,
)

DEVELOPER_PLAN = PlanData(
    marketing_name=PlanMarketingName.FREE.value,
    value=DEFAULT_FREE_PLAN,
    billing_rate=None,
    base_unit_price=PlanPrice.CODECOV_FREE.value,
    benefits=[
        "Up to 1 user",
        "Unlimited public repositories",
        "Unlimited private repositories",
    ],
    tier_name=TierName.TEAM.value,
    trial_days=None,
    monthly_uploads_limit=250,
)

FREE_PLAN_REPRESENTATIONS = {
    PlanName.FREE_PLAN_NAME.value: FREE_PLAN,
    PlanName.BASIC_PLAN_NAME.value: BASIC_PLAN,
    DEFAULT_FREE_PLAN: DEVELOPER_PLAN,
}

TEAM_PLAN_REPRESENTATIONS = {
    PlanName.TEAM_MONTHLY.value: PlanData(
        marketing_name=PlanMarketingName.TEAM.value,
        value=PlanName.TEAM_MONTHLY.value,
        billing_rate=PlanBillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.TEAM_MONTHLY.value,
        benefits=[
            "Up to 10 users",
            "Unlimited repositories",
            "2500 private repo uploads",
            "Patch coverage analysis",
        ],
        tier_name=TierName.TEAM.value,
        trial_days=None,
        monthly_uploads_limit=MonthlyUploadLimits.CODECOV_TEAM_PLAN.value,
    ),
    PlanName.TEAM_YEARLY.value: PlanData(
        marketing_name=PlanMarketingName.TEAM.value,
        value=PlanName.TEAM_YEARLY.value,
        billing_rate=PlanBillingRate.YEARLY.value,
        base_unit_price=PlanPrice.TEAM_YEARLY.value,
        benefits=[
            "Up to 10 users",
            "Unlimited repositories",
            "2500 private repo uploads",
            "Patch coverage analysis",
        ],
        tier_name=TierName.TEAM.value,
        trial_days=None,
        monthly_uploads_limit=MonthlyUploadLimits.CODECOV_TEAM_PLAN.value,
    ),
}

TRIAL_PLAN_REPRESENTATION = {
    PlanName.TRIAL_PLAN_NAME.value: PlanData(
        marketing_name=PlanMarketingName.TRIAL.value,
        value=PlanName.TRIAL_PLAN_NAME.value,
        billing_rate=None,
        base_unit_price=PlanPrice.CODECOV_TRIAL.value,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        tier_name=TierName.TRIAL.value,
        trial_days=None,
        monthly_uploads_limit=None,
    ),
}

PAID_PLANS = {
    **PR_AUTHOR_PAID_USER_PLAN_REPRESENTATIONS,
    **SENTRY_PAID_USER_PLAN_REPRESENTATIONS,
    **ENTERPRISE_CLOUD_USER_PLAN_REPRESENTATIONS,
    **TEAM_PLAN_REPRESENTATIONS,
}

TRIAL_PLANS = {**TRIAL_PLAN_REPRESENTATION}

TEAM_PLANS = {**TEAM_PLAN_REPRESENTATIONS}


USER_PLAN_REPRESENTATIONS = {
    **FREE_PLAN_REPRESENTATIONS,
    **NON_PR_AUTHOR_PAID_USER_PLAN_REPRESENTATIONS,
    **GHM_PLAN_REPRESENTATION,
    **PAID_PLANS,
    **TRIAL_PLANS,
    **TEAM_PLANS,
}

PLANS_THAT_CAN_TRIAL = [
    DEFAULT_FREE_PLAN,
    PlanName.FREE_PLAN_NAME.value,
    PlanName.BASIC_PLAN_NAME.value,
    PlanName.CODECOV_PRO_MONTHLY.value,
    PlanName.CODECOV_PRO_YEARLY.value,
    PlanName.SENTRY_MONTHLY.value,
    PlanName.SENTRY_YEARLY.value,
    PlanName.TRIAL_PLAN_NAME.value,
]

TRIAL_PLAN_SEATS = 1000
TEAM_PLAN_MAX_USERS = 10
