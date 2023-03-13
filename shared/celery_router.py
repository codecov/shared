from shared.billing import BillingPlan, is_enterprise_cloud_plan
from shared.celery_config import BaseCeleryConfig, get_task_group
from shared.config import get_config


def route_tasks_based_on_user_plan(task_name: str, user_plan: str):
    """Helper function to dynamically route tasks based on the user plan.
    This cannot be used as a celery router function directly.
    Returns extra config for the queue, if any.
    """
    default_task_queue = BaseCeleryConfig.task_routes.get(
        task_name, dict(queue=BaseCeleryConfig.task_default_queue)
    )["queue"]
    billing_plan = BillingPlan.from_str(user_plan)
    if is_enterprise_cloud_plan(billing_plan):
        default_enterprise_queue_specific_config = get_config(
            "setup", "tasks", "celery", "enterprise", default=dict()
        )
        this_queue_specific_config = get_config(
            "setup",
            "tasks",
            get_task_group(task_name),
            "enterprise",
            default=default_enterprise_queue_specific_config,
        )
        return {
            "queue": "enterprise_" + default_task_queue,
            "extra_config": this_queue_specific_config,
        }
    return {"queue": default_task_queue, "extra_config": {}}
