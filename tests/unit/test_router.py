from shared.billing import BillingPlan
from shared.celery_config import upload_task_name
from shared.celery_router import route_tasks_based_on_user_plan


def test_route_tasks_based_on_user_plan_defaults():
    assert route_tasks_based_on_user_plan(
        upload_task_name, BillingPlan.users_basic.db_name
    ) == {"queue": "celery"}
    assert route_tasks_based_on_user_plan(
        upload_task_name, BillingPlan.enterprise_cloud_monthly.db_name
    ) == {"queue": "enterprise_celery"}
