from django.test import TestCase
from django.utils import timezone
from shared.django_apps.codecov_metrics.models import UserOnboardingLifeCycleMetrics
from shared.django_apps.codecov_metrics.service.codecov_metrics import (
    UserOnboardingMetricsService,
)


class UserOnboardingMetricsServiceTest(TestCase):
    def setUp(self):
        self.org_id = 1
        self.event = "VISITED_PAGE"
        self.payload = {
            "key1": "value1",
            "key2": 123,
            "key3": [1, 2, 3],
            "key4": {"nested_key": "nested_value"},
        }

    def test_create_user_onboarding_metric_creates_metric(self):
        metric = UserOnboardingMetricsService.create_user_onboarding_metric(
            self.org_id, self.event, self.payload
        )
        self.assertIsNotNone(metric)
        self.assertEqual(metric.org_id, self.org_id)
        self.assertEqual(metric.event, self.event)
        self.assertIsInstance(metric.timestamp, timezone.datetime)
        self.assertEqual(metric.additional_data, self.payload)

    def test_create_user_onboarding_metric_does_not_create_duplicate(self):
        UserOnboardingLifeCycleMetrics.objects.create(
            org_id=self.org_id,
            event=self.event,
            timestamp=timezone.now(),
            additional_data=self.payload,
        )
        metric = UserOnboardingMetricsService.create_user_onboarding_metric(
            self.org_id, self.event, self.payload
        )
        self.assertIsNone(metric)

    def test_create_user_onboarding_metric_with_invalid_event(self):
        invalid_event = "INVALID_EVENT"
        metric = UserOnboardingMetricsService.create_user_onboarding_metric(
            self.org_id, invalid_event, self.payload
        )
        self.assertIsNone(metric)
