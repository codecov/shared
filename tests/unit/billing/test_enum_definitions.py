from shared.billing import BillingPlan


def test_billing_enums():
    assert BillingPlan.users_monthly.db_name == "users-inappm"
    assert BillingPlan.users_yearly.db_name == "users-inappy"
    assert BillingPlan.users_free.db_name == "users-free"
    assert BillingPlan.users_basic.db_name == "users-basic"
    assert BillingPlan.pr_monthly.db_name == "users-pr-inappm"
    assert BillingPlan.pr_yearly.db_name == "users-pr-inappy"
    assert BillingPlan.enterprise_cloud_yearly.db_name == "users-enterprisey"
    assert BillingPlan.enterprise_cloud_monthly.db_name == "users-enterprisem"
