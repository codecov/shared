from shared.billing import BillingPlan
from shared.celery_config import timeseries_backfill_task_name, upload_task_name
from shared.celery_router import route_tasks_based_on_user_plan


def test_route_tasks_based_on_user_plan_defaults():
    assert route_tasks_based_on_user_plan(
        upload_task_name, BillingPlan.users_basic.db_name
    ) == {"queue": "celery", "extra_config": {}}
    assert route_tasks_based_on_user_plan(
        upload_task_name, BillingPlan.enterprise_cloud_monthly.db_name
    ) == {"queue": "enterprise_celery", "extra_config": {}}
    assert route_tasks_based_on_user_plan(
        "misterious_task", BillingPlan.users_basic.db_name
    ) == {"queue": "celery", "extra_config": {}}
    assert route_tasks_based_on_user_plan(
        "misterious_task", BillingPlan.enterprise_cloud_monthly.db_name
    ) == {"queue": "enterprise_celery", "extra_config": {}}


def test_route_tasks_with_config(mock_configuration):
    mock_configuration._params["setup"] = {
        "tasks": {
            "celery": {"enterprise": {"soft_timelimit": 100, "hard_timelimit": 200}},
            "timeseries": {
                "enterprise": {"soft_timelimit": 400, "hard_timelimit": 500}
            },
        }
    }
    assert route_tasks_based_on_user_plan(
        upload_task_name, BillingPlan.users_basic.db_name
    ) == {"queue": "celery", "extra_config": {}}
    assert route_tasks_based_on_user_plan(
        upload_task_name, BillingPlan.enterprise_cloud_monthly.db_name
    ) == {
        "queue": "enterprise_celery",
        "extra_config": {"soft_timelimit": 100, "hard_timelimit": 200},
    }
    assert route_tasks_based_on_user_plan(
        timeseries_backfill_task_name, BillingPlan.enterprise_cloud_monthly.db_name
    ) == {
        "queue": "enterprise_celery",
        "extra_config": {"soft_timelimit": 400, "hard_timelimit": 500},
    }
