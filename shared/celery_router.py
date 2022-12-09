from shared.billing import BillingPlan, is_enterprise_cloud_plan
from shared.celery_config import BaseCeleryConfig


def route_tasks_based_on_user_plan(task_name: str, user_plan: str):
    """Helper function to dynamically route tasks based on the user plan.
    This cannot be used as a celery router function directly.
    """
    default_task_queue = BaseCeleryConfig.task_routes.get(
        task_name, dict(queue=BaseCeleryConfig.task_default_queue)
    )["queue"]
    billing_plan = BillingPlan.from_str(user_plan)
    if is_enterprise_cloud_plan(billing_plan):
        return {"queue": "enterprise_" + default_task_queue}
    return {"queue": default_task_queue}
