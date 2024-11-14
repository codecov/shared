from typing import Literal, Union

from redis import Redis

from shared.config import get_config
from shared.helpers.cache import OurOwnCache, RedisBackend
from shared.helpers.redis import get_redis_url

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
