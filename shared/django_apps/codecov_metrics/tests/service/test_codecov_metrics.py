# tests.py
from django.test import TestCase
from django.utils import timezone
from shared.django_apps.codecov_metrics.models import UserOnboardingLifeCycleMetrics
from shared.django_apps.codecov_metrics.service.codecov_metrics import UserOnboardingMetricsService

class UserOnboardingMetricsServiceTest(TestCase):
    def setUp(self):
        self.org_id = 1
        self.event = "test_event"

    def test_create_user_onboarding_metric_creates_metric(self):
        metric = UserOnboardingMetricsService.create_user_onboarding_metric(
            self.org_id, self.event
        )
        self.assertIsNotNone(metric)
        self.assertEqual(metric.org_id, self.org_id)
        self.assertEqual(metric.event, self.event)
        self.assertIsInstance(metric.timestamp, timezone.datetime)

    def test_create_user_onboarding_metric_does_not_create_duplicate(self):
        UserOnboardingLifeCycleMetrics.objects.create(
            org_id=self.org_id, event=self.event, timestamp=timezone.now()
        )
        metric = UserOnboardingMetricsService.create_user_onboarding_metric(
            self.org_id, self.event
        )
        self.assertIsNone(metric)
