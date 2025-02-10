from django.test import TestCase

from shared.django_apps.bundle_analysis.models import CacheConfig
from shared.django_apps.bundle_analysis.service.bundle_analysis import (
    BundleAnalysisCacheConfigService,
)


class BundleAnalysisCacheConfigServiceTest(TestCase):
    def test_bundle_config_create_then_update(self):
        # Create
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1, name="bundle1", is_caching=True
        )

        query_results = CacheConfig.objects.all()
        assert len(query_results) == 1

        data = query_results[0]
        create_stamp, update_stamp = data.created_at, data.updated_at

        assert data.repo_id == 1
        assert data.bundle_name == "bundle1"
        assert data.is_caching == True
        assert create_stamp is not None
        assert update_stamp is not None

        # Update
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1, name="bundle1", is_caching=False
        )

        query_results = CacheConfig.objects.all()
        assert len(query_results) == 1

        data = query_results[0]
        create_stamp_updated, update_stamp_updated = data.created_at, data.updated_at

        assert data.repo_id == 1
        assert data.bundle_name == "bundle1"
        assert data.is_caching == False
        assert create_stamp_updated == create_stamp
        assert update_stamp_updated != update_stamp

    def test_bundle_config_create_multiple(self):
        # Create 1
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1, name="bundleA", is_caching=False
        )

        # Create 2
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1, name="bundleB", is_caching=True
        )

        # Create 3
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=2, name="bundleA", is_caching=False
        )

        # Create 4
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=2, name="bundleB", is_caching=True
        )

        query_results = CacheConfig.objects.all()
        assert len(query_results) == 4

    def test_bundle_config_get_or_create(self):
        # Create 1 -- default as is_caching=True
        BundleAnalysisCacheConfigService.create_if_not_exists(repo_id=1, name="bundleA")
        query_results = CacheConfig.objects.all()
        assert len(query_results) == 1
        assert query_results[0].repo_id == 1
        assert query_results[0].bundle_name == "bundleA"
        assert query_results[0].is_caching == True

        # Create 2 -- already exist don't change is_caching value
        BundleAnalysisCacheConfigService.create_if_not_exists(
            repo_id=1, name="bundleA", is_caching=False
        )
        query_results = CacheConfig.objects.all()
        assert len(query_results) == 1
        assert query_results[0].repo_id == 1
        assert query_results[0].bundle_name == "bundleA"
        assert query_results[0].is_caching == True

        # Create 3 -- new bundle
        BundleAnalysisCacheConfigService.create_if_not_exists(
            repo_id=1, name="bundleB", is_caching=False
        )
        query_results = CacheConfig.objects.all()
        assert len(query_results) == 2
        query_results = CacheConfig.objects.filter(bundle_name="bundleA").all()
        assert len(query_results) == 1
        assert query_results[0].repo_id == 1
        assert query_results[0].bundle_name == "bundleA"
        assert query_results[0].is_caching == True
        query_results = CacheConfig.objects.filter(bundle_name="bundleB").all()
        assert len(query_results) == 1
        assert query_results[0].repo_id == 1
        assert query_results[0].bundle_name == "bundleB"
        assert query_results[0].is_caching == False

    def test_bundle_config_get_cache_option(self):
        # Does not exist
        assert (
            BundleAnalysisCacheConfigService.get_cache_option(repo_id=1, name="bundleA")
            == False
        )

        # Create
        BundleAnalysisCacheConfigService.create_if_not_exists(repo_id=1, name="bundleA")
        assert (
            BundleAnalysisCacheConfigService.get_cache_option(repo_id=1, name="bundleA")
            == True
        )

        # Update
        BundleAnalysisCacheConfigService.update_cache_option(
            repo_id=1, name="bundleA", is_caching=False
        )
        assert (
            BundleAnalysisCacheConfigService.get_cache_option(repo_id=1, name="bundleA")
            == False
        )

        # Create another 2 bundles
        BundleAnalysisCacheConfigService.create_if_not_exists(
            repo_id=1, name="bundleB", is_caching=True
        )
        BundleAnalysisCacheConfigService.create_if_not_exists(
            repo_id=2, name="bundleA", is_caching=True
        )
        assert (
            BundleAnalysisCacheConfigService.get_cache_option(repo_id=1, name="bundleA")
            == False
        )
