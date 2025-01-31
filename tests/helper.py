from json import dumps

from shared.django_apps.codecov_auth.models import BillingRate
from shared.django_apps.codecov_auth.tests.factories import PlanFactory, TierFactory
from shared.plan.constants import (
    PlanName,
    PlanPrice,
    TierName,
)


def v2_to_v3(report):
    def _sessions(sessions):
        if sessions:
            return [
                [int(sid), data.get("p") or data["c"], data.get("b")]
                for sid, data in sessions.items()
            ]
        return None

    files = {}
    chunks = []
    for loc, (fname, data) in enumerate(report.get("files", {}).items()):
        totals = data.get("t", {}).get
        files[fname] = [
            loc,
            [totals(k, 0) for k in "fnhmpcbdMs"] if totals("n") else None,
        ]
        chunk = [""]
        if data.get("l"):
            lines = data["l"].get
            for ln in range(1, max(list(map(int, list(data["l"].keys())))) + 1):
                line = lines(str(ln))
                if line:
                    chunk.append(
                        dumps(
                            [
                                line.get("c"),
                                line.get("t"),
                                _sessions(line.get("s")),
                                None,
                            ]
                        )
                    )
                else:
                    chunk.append("")
        chunks.append("\n".join(chunk))

    return {
        "files": files,
        "sessions": dict(
            [(int(sid), data) for sid, data in report.get("sessions", {}).items()]
        ),
        "totals": report.get("totals", {}),
        "chunks": chunks,
    }


def mock_all_plans_and_tiers():
    trial_tier = TierFactory(tier_name=TierName.TRIAL.value)
    PlanFactory(
        tier=trial_tier,
        name=PlanName.TRIAL_PLAN_NAME.value,
        paid_plan=False,
        marketing_name="Developer",
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
    )

    basic_tier = TierFactory(tier_name=TierName.BASIC.value)
    PlanFactory(
        name=PlanName.BASIC_PLAN_NAME.value,
        tier=basic_tier,
        marketing_name="Developer",
        benefits=[
            "Up to 1 user",
            "Unlimited public repositories",
            "Unlimited private repositories",
        ],
        monthly_uploads_limit=250,
    )
    PlanFactory(
        name=PlanName.FREE_PLAN_NAME.value,
        tier=basic_tier,
        marketing_name="Developer",
        benefits=[
            "Up to 1 user",
            "Unlimited public repositories",
            "Unlimited private repositories",
        ],
    )

    pro_tier = TierFactory(tier_name=TierName.PRO.value)
    PlanFactory(
        name=PlanName.CODECOV_PRO_MONTHLY.value,
        tier=pro_tier,
        marketing_name="Pro",
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        billing_rate=BillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        paid_plan=True,
    )
    PlanFactory(
        name=PlanName.CODECOV_PRO_YEARLY.value,
        tier=pro_tier,
        marketing_name="Pro",
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        billing_rate=BillingRate.ANNUALLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        paid_plan=True,
    )

    team_tier = TierFactory(tier_name=TierName.TEAM.value)
    PlanFactory(
        name=PlanName.TEAM_MONTHLY.value,
        tier=team_tier,
        marketing_name="Team",
        benefits=[
            "Up to 10 users",
            "Unlimited repositories",
            "2500 private repo uploads",
            "Patch coverage analysis",
        ],
        billing_rate=BillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.TEAM_MONTHLY.value,
        monthly_uploads_limit=2500,
        paid_plan=True,
    )
    PlanFactory(
        name=PlanName.TEAM_YEARLY.value,
        tier=team_tier,
        marketing_name="Team",
        benefits=[
            "Up to 10 users",
            "Unlimited repositories",
            "2500 private repo uploads",
            "Patch coverage analysis",
        ],
        billing_rate=BillingRate.ANNUALLY.value,
        base_unit_price=PlanPrice.TEAM_YEARLY.value,
        monthly_uploads_limit=2500,
        paid_plan=True,
    )

    sentry_tier = TierFactory(tier_name=TierName.SENTRY.value)
    PlanFactory(
        name=PlanName.SENTRY_MONTHLY.value,
        tier=sentry_tier,
        marketing_name="Sentry Pro",
        billing_rate=BillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        paid_plan=True,
        benefits=[
            "Includes 5 seats",
            "$12 per additional seat",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
    )
    PlanFactory(
        name=PlanName.SENTRY_YEARLY.value,
        tier=sentry_tier,
        marketing_name="Sentry Pro",
        billing_rate=BillingRate.ANNUALLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        paid_plan=True,
        benefits=[
            "Includes 5 seats",
            "$10 per additional seat",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
    )

    enterprise_tier = TierFactory(tier_name=TierName.ENTERPRISE.value)
    PlanFactory(
        name=PlanName.ENTERPRISE_CLOUD_MONTHLY.value,
        tier=enterprise_tier,
        marketing_name="Enterprise Cloud",
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        billing_rate=BillingRate.MONTHLY.value,
        base_unit_price=PlanPrice.MONTHLY.value,
        paid_plan=True,
    )
    PlanFactory(
        name=PlanName.ENTERPRISE_CLOUD_YEARLY.value,
        tier=enterprise_tier,
        marketing_name="Enterprise Cloud",
        billing_rate=BillingRate.ANNUALLY.value,
        base_unit_price=PlanPrice.YEARLY.value,
        paid_plan=True,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
    )
