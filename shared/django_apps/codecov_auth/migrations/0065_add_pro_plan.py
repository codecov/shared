from django.db import migrations


def add_pro_plan(apps, schema_editor):
    Plan = apps.get_model("codecov_auth", "Plan")
    Tier = apps.get_model("codecov_auth", "Tier")

    pro_tier = Tier.objects.create(
        tier_name="pro",
        bundle_analysis=True,
        test_analytics=True,
        flaky_test_detection=True,
        project_coverage=True,
        private_repo_support=True,
    )

    Plan.objects.create(
        tier=pro_tier,
        base_unit_price=10,
        benefits=[
            "Configurable # of users",
            "Unlimited public repositories",
            "Unlimited private repositories",
            "Priority Support",
        ],
        billing_rate="annually",
        is_active=True,
        marketing_name="Pro",
        max_seats=None,
        monthly_uploads_limit=None,
        name="users-pr-inappy",
        paid_plan=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("codecov_auth", "0064_plan_stripe_id"),
    ]

    operations = [
        migrations.RunPython(add_pro_plan),
    ]
