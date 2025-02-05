from django.db import migrations

from shared.django_apps.utils.config import RUN_ENV


def add_pro_plan(apps, schema_editor):
    if RUN_ENV != "ENTERPRISE":
        return

    Plan = apps.get_model("codecov_auth", "Plan")
    Tier = apps.get_model("codecov_auth", "Tier")
    Owner = apps.get_model("codecov_auth", "Owner")
    Account = apps.get_model("codecov_auth", "Account")

    pro_tier, _ = Tier.objects.get_or_create(
        tier_name="pro",
        bundle_analysis=True,
        test_analytics=True,
        flaky_test_detection=True,
        project_coverage=True,
        private_repo_support=True,
    )

    Plan.objects.get_or_create(
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

    for owner in Owner.objects.all():
        owner.plan = "users-pr-inappy"
        owner.save()

    for account in Account.objects.all():
        account.plan = "users-pr-inappy"
        account.save()


class Migration(migrations.Migration):
    dependencies = [
        ("codecov_auth", "0065_alter_account_plan_alter_owner_plan"),
    ]

    operations = [
        migrations.RunPython(add_pro_plan),
    ]
