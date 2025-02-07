from django.conf import settings
from django.db import migrations


def add_pro_plan(apps, schema_editor):
    # if RUN_ENV == "ENTERPRISE":
    #     return

    Plan = apps.get_model("codecov_auth", "Plan")
    Tier = apps.get_model("codecov_auth", "Tier")
    Owner = apps.get_model("codecov_auth", "Owner")
    Account = apps.get_model("codecov_auth", "Account")

    defaults = {
        "bundle_analysis": True,
        "test_analytics": True,
        "flaky_test_detection": True,
        "project_coverage": True,
        "private_repo_support": True,
    }
    pro_tier, _ = Tier.objects.update_or_create(
        tier_name="pro",
        defaults=defaults,
    )

    plan_defaults = {
        "tier": pro_tier,
        "base_unit_price": 10,
        "benefits": [
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        "billing_rate": "annually",
        "is_active": True,
        "marketing_name": "Pro",
        "max_seats": None,
        "monthly_uploads_limit": None,
        "paid_plan": True,
    }

    Plan.objects.update_or_create(
        name=settings.DEFAULT_PLAN_NAME,
        defaults=plan_defaults,
    )

    Owner.objects.all().update(plan=settings.DEFAULT_PLAN_NAME)

    Account.objects.all().update(plan=settings.DEFAULT_PLAN_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ("codecov_auth", "0065_alter_account_plan_alter_owner_plan"),
    ]

    operations = [
        migrations.RunPython(add_pro_plan),
    ]
