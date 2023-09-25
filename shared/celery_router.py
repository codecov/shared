import fnmatch
import re
from collections import OrderedDict
from collections.abc import Mapping

from shared.billing import BillingPlan, is_enterprise_cloud_plan
from shared.celery_config import BaseCeleryConfig, get_task_group
from shared.config import get_config

Pattern = re.Pattern


# based on code from https://github.com/celery/celery/blob/main/celery/app/routes.py
class MapRoute:
    def __init__(self, map):
        map = map.items() if isinstance(map, Mapping) else map
        self.map = {}
        self.patterns = OrderedDict()
        for k, v in map:
            if isinstance(k, Pattern):
                self.patterns[k] = v
            elif "*" in k:
                self.patterns[re.compile(fnmatch.translate(k))] = v
            else:
                self.map[k] = v

    def __call__(self, name, *args, **kwargs):
        try:
            return dict(self.map[name])
        except KeyError:
            pass
        except ValueError:
            return {"queue": self.map[name]}
        for regex, route in self.patterns.items():
            if regex.match(name):
                try:
                    return dict(route)
                except ValueError:
                    return {"queue": route}


def route_tasks_based_on_user_plan(task_name: str, user_plan: str):
    """Helper function to dynamically route tasks based on the user plan.
    This cannot be used as a celery router function directly.
    Returns extra config for the queue, if any.
    """
    route = MapRoute(BaseCeleryConfig.task_routes)
    default_task_queue = (
        route(task_name) or dict(queue=BaseCeleryConfig.task_default_queue)
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
