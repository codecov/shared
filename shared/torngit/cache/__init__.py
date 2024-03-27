from typing import Union

from redis import Redis
from typing_extensions import Literal

from shared.config import get_config
from shared.helpers.cache import OurOwnCache, RedisBackend


def get_redis_url() -> str:
    url = get_config("services", "redis_url")
    if url is not None:
        return url
    hostname = "redis"
    port = 6379
    return f"redis://{hostname}:{port}"


def get_redis_connection() -> Redis:
    url = get_redis_url()
    return _get_redis_instance_from_url(url)


def _get_redis_instance_from_url(url):
    return Redis.from_url(url)


CachedEndpoint = Union[Literal["check"], Literal["compare"], Literal["status"]]


class TorngitCache(OurOwnCache):
    def __init__(self):
        super().__init__()
        self.ttls = {}
        self._initialized = False
        self._enabled = False

    def initialize(self) -> None:
        """Initializes and configures the TorngitCache according to config."""
        if self.is_initialized:
            return
        use_cache = get_config("services", "vcs_cache", "enabled", default=False)
        if use_cache:
            redis = Redis.from_url(get_redis_url())
            backend = RedisBackend(redis_connection=redis)
            app = get_config("services", "vcs_cache", "metrics_app", default=None)
            self.configure(backend=backend, app=app)
            self._enabled = True
        ttls = {
            "check": get_config("services", "vcs_cache", "check_duration", default=120),
            "compare": get_config(
                "services", "vcs_cache", "compare_duration", default=120
            ),
            "status": get_config(
                "services", "vcs_cache", "status_duration", default=120
            ),
        }
        self.ttls = ttls
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def get_ttl(self, endpoint: CachedEndpoint) -> dict:
        return self.ttls.get(endpoint, 120)


# This instance is shared among all the Torngit instances created on the same process.
# It doesn't matter because the cache is distributed and configuration can't change
# between these instances, so it's ok to share the same cache.
torngit_cache = TorngitCache()
