import pytest
from django.test import override_settings

from shared.billing import BillingPlan, is_enterprise_cloud_plan, is_pr_billing_plan
from shared.django_apps.codecov_auth.tests.factories import OwnerFactory


@pytest.fixture
def dbsession(db):
    return db


@override_settings(IS_ENTERPRISE=False)
def test_pr_author_plan_check(dbsession, mock_configuration):
    owner = OwnerFactory(service="github", plan="users-pr-inappm")
    if dbsession is not None:
        dbsession.add(owner)
        dbsession.flush()
    assert is_pr_billing_plan(owner.plan)


@override_settings(IS_ENTERPRISE=True)
def test_pr_author_enterprise_plan_check(dbsession, mock_configuration):
    owner = OwnerFactory(service="github")
    if dbsession is not None:
        dbsession.add(owner)
        dbsession.flush()

    encrypted_license = "wxWEJyYgIcFpi6nBSyKQZQeaQ9Eqpo3SXyUomAqQOzOFjdYB3A8fFM1rm+kOt2ehy9w95AzrQqrqfxi9HJIb2zLOMOB9tSy52OykVCzFtKPBNsXU/y5pQKOfV7iI3w9CHFh3tDwSwgjg8UsMXwQPOhrpvl2GdHpwEhFdaM2O3vY7iElFgZfk5D9E7qEnp+WysQwHKxDeKLI7jWCnBCBJLDjBJRSz0H7AfU55RQDqtTrnR+rsLDHOzJ80/VxwVYhb"
    mock_configuration.params["setup"]["enterprise_license"] = encrypted_license
    mock_configuration.params["setup"]["codecov_dashboard_url"] = (
        "https://codecov.mysite.com"
    )

    assert is_pr_billing_plan(owner.plan)


@override_settings(IS_ENTERPRISE=False)
def test_plan_not_pr_author(dbsession, mock_configuration):
    owner = OwnerFactory(service="github", plan=BillingPlan.users_monthly.value)
    if dbsession is not None:
        dbsession.add(owner)
        dbsession.flush()

    assert not is_pr_billing_plan(owner.plan)


@override_settings(IS_ENTERPRISE=True)
def test_pr_author_enterprise_plan_check_non_pr_plan(dbsession, mock_configuration):
    owner = OwnerFactory(service="github")
    if dbsession is not None:
        dbsession.add(owner)
        dbsession.flush()

    encrypted_license = "0dRbhbzp8TVFQp7P4e2ES9lSfyQlTo8J7LQ"
    mock_configuration.params["setup"]["enterprise_license"] = encrypted_license
    mock_configuration.params["setup"]["codecov_dashboard_url"] = (
        "https://codeov.mysite.com"
    )

    assert not is_pr_billing_plan(owner.plan)


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
