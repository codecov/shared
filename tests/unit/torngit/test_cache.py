from shared.helpers.cache import NullBackend, RedisBackend
from shared.torngit.cache import torngit_cache


class TestTorngitCacheConfig(object):
    def test_initialize_active(self, mock_configuration, mocker):
        # Manually return torngit cache to default state
        # Because other tests might have messed with it
        torngit_cache._enabled = False
        torngit_cache._initialized = False
        torngit_cache.configure(NullBackend())
        # Now we initialize
        mock_configuration.set_params(
            {
                "services": {
                    "vcs_cache": {
                        "enabled": True,
                        "check_duration": 100,
                        "compare_duration": 80,
                        "status_duration": 60,
                        "metrics_app": "worker",
                    }
                }
            }
        )
        torngit_cache.initialize()
        assert isinstance(torngit_cache._backend, RedisBackend)
        assert torngit_cache.is_initialized == True
        assert torngit_cache.get_ttl("check") == 100
        assert torngit_cache.get_ttl("compare") == 80
        assert torngit_cache.get_ttl("status") == 60
        assert torngit_cache.is_enabled == True
        # Now we test that by calling init_torngit_cache again
        # It will do nothing since the cache is initialized
        mock_get_redis = mocker.patch("shared.torngit.cache.get_redis_url")
        torngit_cache.initialize()
        assert torngit_cache.is_initialized == True
        assert torngit_cache.is_enabled == True
        mock_get_redis.assert_not_called()

    def test_initialize_not_active(self, mock_configuration):
        # Manually return torngit cache to default state
        # Because other tests might have messed with it
        torngit_cache._enabled = False
        torngit_cache._initialized = False
        torngit_cache.configure(NullBackend())
        # Now we initialize it
        mock_configuration.set_params({"services": {"vcs_cache": {"enabled": False}}})
        torngit_cache.initialize()
        assert torngit_cache.is_initialized == True
        assert torngit_cache.is_enabled == False
        assert isinstance(torngit_cache._backend, NullBackend)
        assert torngit_cache.get_ttl("check") == 120
        assert torngit_cache.get_ttl("compare") == 120
        assert torngit_cache.get_ttl("status") == 120
