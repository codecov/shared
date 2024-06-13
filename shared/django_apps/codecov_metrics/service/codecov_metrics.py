import logging
from typing import Any, Dict

from django.utils import timezone

from ..models import UserOnboardingLifeCycleMetrics

log = logging.getLogger(__name__)


class UserOnboardingMetricsService:
    ALLOWED_EVENTS = {
        "VISITED_PAGE",
        "CLICKED_BUTTON",
        "COPIED_TEXT",
        "COMPLETED_UPLOAD",
        "INSTALLED_APP",
    }

    @staticmethod
    def create_user_onboarding_metric(org_id: int, event: str, payload: Dict[str, Any]):
        if event not in UserOnboardingMetricsService.ALLOWED_EVENTS:
            log.warning("Incompatible event type", extra=dict(event_name=event))
            return

        if not UserOnboardingLifeCycleMetrics.objects.filter(
            org_id=org_id, event=event
        ).exists():
            metric = UserOnboardingLifeCycleMetrics(
                org_id=org_id,
                event=event,
                timestamp=timezone.now(),
                additional_data=payload,
            )
            metric.save()
            return metric
        return None
