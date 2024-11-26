from shared.billing import BillingPlan, is_enterprise_cloud_plan, is_pr_billing_plan


def test_billing_enums():
    assert BillingPlan.users_monthly.db_name == "users-inappm"
    assert BillingPlan.users_yearly.db_name == "users-inappy"
    assert BillingPlan.users_free.db_name == "users-free"
    assert BillingPlan.users_basic.db_name == "users-basic"
    assert BillingPlan.pr_monthly.db_name == "users-pr-inappm"
    assert BillingPlan.pr_yearly.db_name == "users-pr-inappy"
    assert BillingPlan.enterprise_cloud_yearly.db_name == "users-enterprisey"
    assert BillingPlan.enterprise_cloud_monthly.db_name == "users-enterprisem"
    assert BillingPlan.team_monthly.db_name == "users-teamm"
    assert BillingPlan.team_yearly.db_name == "users-teamy"


def test_get_from_string():
    assert BillingPlan.from_str("users-inappm") == BillingPlan.users_monthly
    assert BillingPlan.from_str("users-inappy") == BillingPlan.users_yearly
    assert BillingPlan.from_str("users-free") == BillingPlan.users_free
    assert BillingPlan.from_str("users-basic") == BillingPlan.users_basic
    assert BillingPlan.from_str("users-pr-inappm") == BillingPlan.pr_monthly
    assert BillingPlan.from_str("users-pr-inappy") == BillingPlan.pr_yearly
    assert (
        BillingPlan.from_str("users-enterprisey") == BillingPlan.enterprise_cloud_yearly
    )
    assert (
        BillingPlan.from_str("users-enterprisem")
        == BillingPlan.enterprise_cloud_monthly
    )
    assert BillingPlan.from_str("users-teamm") == BillingPlan.team_monthly
    assert BillingPlan.from_str("users-teamy") == BillingPlan.team_yearly


def test_is_enterprise_cloud_plan():
    assert not is_enterprise_cloud_plan(BillingPlan.pr_monthly)
    assert not is_enterprise_cloud_plan(BillingPlan.pr_yearly)
    assert is_enterprise_cloud_plan(BillingPlan.enterprise_cloud_yearly)
    assert is_enterprise_cloud_plan(BillingPlan.enterprise_cloud_monthly)


def test_is_pr_billing_plan():
    assert is_pr_billing_plan(BillingPlan.pr_monthly)
    assert is_pr_billing_plan(BillingPlan.pr_yearly)
    assert not is_pr_billing_plan(BillingPlan.enterprise_cloud_yearly)
    assert not is_pr_billing_plan(BillingPlan.enterprise_cloud_monthly)
    assert not is_pr_billing_plan(BillingPlan.team_monthly)
    assert not is_pr_billing_plan(BillingPlan.team_yearly)
