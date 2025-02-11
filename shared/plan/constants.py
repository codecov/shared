import enum

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


TRIAL_PLAN_SEATS = 1000
TEAM_PLAN_MAX_USERS = 10
