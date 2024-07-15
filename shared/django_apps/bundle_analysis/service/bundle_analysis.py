from shared.django_apps.bundle_analysis.models import CacheConfig


class BundleAnalysisCacheConfigService:
    @staticmethod
    def update_cache_option(repo_id, name, is_caching=True) -> None:
        CacheConfig.objects.update_or_create(
            repo_id=repo_id, bundle_name=name, defaults={"is_caching": is_caching}
        )
