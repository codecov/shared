from unittest.mock import patch

import pytest

from shared.celery_config import timeseries_backfill_task_name, upload_task_name
from shared.celery_router import route_tasks_based_on_user_plan
from shared.plan.constants import DEFAULT_FREE_PLAN, PlanName
from tests.helper import mock_all_plans_and_tiers


class TestCeleryRouter:
    @pytest.mark.django_db
    def test_route_tasks_based_on_user_plan_defaults(self):
        mock_all_plans_and_tiers()
        assert route_tasks_based_on_user_plan(upload_task_name, DEFAULT_FREE_PLAN) == {
            "queue": "celery",
            "extra_config": {},
        }
        assert route_tasks_based_on_user_plan(
            upload_task_name, PlanName.ENTERPRISE_CLOUD_MONTHLY.value
        ) == {"queue": "enterprise_celery", "extra_config": {}}
        assert route_tasks_based_on_user_plan("misterious_task", DEFAULT_FREE_PLAN) == {
            "queue": "celery",
            "extra_config": {},
        }
        assert route_tasks_based_on_user_plan(
            "misterious_task", PlanName.ENTERPRISE_CLOUD_MONTHLY.value
        ) == {"queue": "enterprise_celery", "extra_config": {}}

    @pytest.mark.django_db
    def test_route_tasks_with_config(self, mock_configuration):
        mock_all_plans_and_tiers()
        mock_configuration._params["setup"] = {
            "tasks": {
                "celery": {
                    "enterprise": {"soft_timelimit": 100, "hard_timelimit": 200}
                },
                "timeseries": {
                    "enterprise": {"soft_timelimit": 400, "hard_timelimit": 500}
                },
            }
        }
        assert route_tasks_based_on_user_plan(upload_task_name, DEFAULT_FREE_PLAN) == {
            "queue": "celery",
            "extra_config": {},
        }
        assert route_tasks_based_on_user_plan(
            upload_task_name, PlanName.ENTERPRISE_CLOUD_MONTHLY.value
        ) == {
            "queue": "enterprise_celery",
            "extra_config": {"soft_timelimit": 100, "hard_timelimit": 200},
        }
        assert route_tasks_based_on_user_plan(
            timeseries_backfill_task_name, PlanName.ENTERPRISE_CLOUD_MONTHLY.value
        ) == {
            "queue": "enterprise_celery",
            "extra_config": {"soft_timelimit": 400, "hard_timelimit": 500},
        }

    @patch.dict(
        "shared.celery_config.BaseCeleryConfig.task_routes",
        {"app.tasks.upload.*": {"queue": "uploads"}},
    )
    @pytest.mark.django_db
    def test_route_tasks_with_glob_config(self, mocker):
        mock_all_plans_and_tiers()
        assert route_tasks_based_on_user_plan(upload_task_name, DEFAULT_FREE_PLAN) == {
            "queue": "uploads",
            "extra_config": {},
        }
        assert route_tasks_based_on_user_plan(
            upload_task_name, PlanName.ENTERPRISE_CLOUD_MONTHLY.value
        ) == {"queue": "enterprise_uploads", "extra_config": {}}
