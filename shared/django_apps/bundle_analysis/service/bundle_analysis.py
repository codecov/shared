from shared.django_apps.bundle_analysis.models import CacheConfig


class BundleAnalysisCacheConfigService:
    @staticmethod
    def update_cache_option(repo_id: int, name: str, is_caching: bool = True) -> None:
        CacheConfig.objects.update_or_create(
            repo_id=repo_id, bundle_name=name, defaults={"is_caching": is_caching}
        )

    @staticmethod
    def create_if_not_exists(repo_id: int, name: str, is_caching: bool = True) -> None:
        CacheConfig.objects.get_or_create(
            repo_id=repo_id, bundle_name=name, defaults={"is_caching": is_caching}
        )

    @staticmethod
    def get_cache_option(repo_id: int, name: str) -> bool:
        cache_option = CacheConfig.objects.filter(
            repo_id=repo_id, bundle_name=name
        ).first()
        return cache_option.is_caching if cache_option else False
