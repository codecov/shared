# services.py
from django.utils import timezone
from ..models import UserOnboardingLifeCycleMetrics

class UserOnboardingMetricsService:
    @staticmethod
    def create_user_onboarding_metric(org_id: int, event: str):
        if not UserOnboardingLifeCycleMetrics.objects.filter(org_id=org_id, event=event).exists():
            metric = UserOnboardingLifeCycleMetrics(
                org_id=org_id,
                event=event,
                timestamp=timezone.now()
            )
            metric.save()
            return metric
        return None

