from django.test import TestCase
from django.utils import timezone
from shared.django_apps.codecov_metrics.models import UserOnboardingLifeCycleMetrics
from shared.django_apps.codecov_metrics.service.codecov_metrics import (
    UserOnboardingMetricsService,
)

from shared.django_apps.bundle_analysis_app.service.bundle_analysis import BundleAnalysisCacheConfigService
from shared.django_apps.bundle_analysis_app.models import CacheConfig

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

    def test_bundle_config_create_then_update(self):
        # Create
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1,
            name="bundle1",
            is_caching=True
        )

        query_results = CacheConfig.objects.all()
        assert len(query_results) == 1

        data = query_results[0]
        create_stamp, update_stamp = data.created_at, data.updated_at

        assert data.repo_id==1
        assert data.bundle_name=="bundle1"
        assert data.is_caching==True
        assert create_stamp is not None
        assert update_stamp is not None

        # Update
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1,
            name="bundle1",
            is_caching=False
        )

        query_results = CacheConfig.objects.all()
        assert len(query_results) == 1

        data = query_results[0]
        create_stamp_updated, update_stamp_updated = data.created_at, data.updated_at

        assert data.repo_id==1
        assert data.bundle_name=="bundle1"
        assert data.is_caching==False
        assert create_stamp_updated == create_stamp
        assert update_stamp_updated != update_stamp