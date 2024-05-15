import pickle

import pytest
from redis.exceptions import TimeoutError

from shared.helpers.cache import (
    NO_VALUE,
    BaseBackend,
    LogMapping,
    OurOwnCache,
    RedisBackend,
    make_hash_sha256,
)
from shared.helpers.cache import log as cache_log


class RandomCounter(object):
    def __init__(self):
        self.value = 0

    def call_function(self):
        self.value += 1
        return self.value

    def call_function_args(self, base, head, something=None, danger=True):
        return base + head

    async def async_call_function(self):
        self.value += 2
        self.value *= 4
        return self.value

    async def async_call_function_args(self, base, head, something=None, danger=True):
        return base + head


class FakeBackend(BaseBackend):
    def __init__(self):
        self.all_keys = {}

    def get(self, key):
        possible_values = self.all_keys.get(key, {})
        for ttl, val in possible_values.items():
            return val
        return NO_VALUE

    def set(self, key, ttl, value):
        if key not in self.all_keys:
            self.all_keys[key] = {}
        self.all_keys[key][ttl] = value


class FakeRedis(object):
    def __init__(self):
        self.all_keys = {}

    def get(self, key):
        return self.all_keys.get(key)

    def setex(self, key, expire, value):
        self.all_keys[key] = value


class FakeRedisWithIssues(object):
    def get(self, key):
        raise TimeoutError()

    def setex(self, key, expire, value):
        raise TimeoutError()


class TestRedisBackend(object):
    def test_simple_redis_call(self):
        redis_backend = RedisBackend(FakeRedis())
        assert redis_backend.get("normal_key") == NO_VALUE
        redis_backend.set("normal_key", 120, {"value_1": set("ascdefgh"), 1: [1, 3]})
        assert redis_backend.get("normal_key") == {
            "value_1": set("ascdefgh"),
            1: [1, 3],
        }

    def test_simple_redis_call_invalid_pickle_version(self):
        redis_instance = FakeRedis()
        # PICKLE HERE WILL BE SET TO VERSION 9 (\x09 in the second byte of the value)
        # IF THIS STOPS FAILING WITH ValueError, CHANGE THE SECOND BYTE TO SOMETHING HIGHER
        redis_instance.setex("key", 120, b"\x80\x09X\x05\x00\x00\x00valueq\x00.")
        redis_backend = RedisBackend(redis_instance)
        assert redis_backend.get("key") == NO_VALUE

    def test_simple_redis_call_exception(self):
        redis_backend = RedisBackend(FakeRedisWithIssues())
        assert redis_backend.get("normal_key") == NO_VALUE
        redis_backend.set("normal_key", 120, {"value_1": set("ascdefgh"), 1: [1, 3]})
        assert redis_backend.get("normal_key") == NO_VALUE


class TestCache(object):
    def test_simple_caching_no_backend_no_params(self, mocker):
        cache = OurOwnCache()
        sample_function = RandomCounter().call_function
        cached_function = cache.cache_function()(sample_function)
        assert cached_function() == 1
        assert cached_function() == 2
        assert cached_function() == 3

    def test_simple_caching_no_backend_no_params_with_ttl(self, mocker):
        cache = OurOwnCache()
        sample_function = RandomCounter().call_function
        cached_function = cache.cache_function(ttl=300)(sample_function)
        assert cached_function() == 1
        assert cached_function() == 2
        assert cached_function() == 3

    @pytest.mark.asyncio
    async def test_simple_caching_no_backend_async_no_params(self, mocker):
        cache = OurOwnCache()
        assert cache._app == "not_configured"
        sample_function = RandomCounter().async_call_function
        cached_function = cache.cache_function()(sample_function)
        assert (await cached_function()) == 8
        assert (await cached_function()) == 40
        assert (await cached_function()) == 168

    def test_simple_caching_fake_backend_no_params(self, mocker):
        cache = OurOwnCache()
        cache.configure(FakeBackend())
        assert cache._app == "shared"
        sample_function = RandomCounter().call_function
        cached_function = cache.cache_function()(sample_function)
        assert cached_function() == 1
        assert cached_function() == 1
        assert cached_function() == 1

    def test_simple_caching_fake_backend_with_params(self, mocker):
        mock_log = mocker.patch.object(cache_log, "info")
        log_map = LogMapping(
            {
                "args_indexes_to_log": [0, 1],
                "kwargs_keys_to_log": ["base", "head", "something"],
            }
        )
        cache = OurOwnCache()
        cache.configure(FakeBackend())
        assert cache._app == "shared"
        sample_function = RandomCounter().call_function_args
        cached_function = cache.cache_function(log_hits=True, log_map=log_map)(
            sample_function
        )
        assert cached_function("base", "head", something="batata") == "basehead"
        mock_log.assert_not_called()  # not a hit, not logger
        assert cached_function("base", "head", something="else") == "basehead"
        mock_log.assert_not_called()  # not a hit, not logger
        assert cached_function("base", "head", something="else") == "basehead"
        assert mock_log.call_count == 1
        args, kwargs = mock_log.call_args
        assert args == ("Returning cache hit",)
        assert "extra" in kwargs
        extra_logged = kwargs["extra"]
        extra_args = extra_logged["fn_args"]
        extra_kwargs = extra_logged["fn_kwargs"]
        assert extra_args == ["base", "head"]
        assert extra_kwargs == {
            "something": "else"
        }  # Notice that danger is not part of it
        # Changing the way we call the function
        assert cached_function("base", head="head", something="else") == "basehead"
        assert mock_log.call_count == 1  # This is not cached because the args changed
        assert cached_function("base", head="head", something="else") == "basehead"
        assert mock_log.call_count == 2
        args, kwargs = mock_log.call_args
        assert args == ("Returning cache hit",)
        assert "extra" in kwargs
        extra_logged = kwargs["extra"]
        extra_args = extra_logged["fn_args"]
        extra_kwargs = extra_logged["fn_kwargs"]
        assert extra_args == ["base"]
        assert extra_kwargs == {
            "head": "head",
            "something": "else",
        }  # Notice that danger is not part of it

    @pytest.mark.asyncio
    async def test_simple_caching_fake_backend_async_no_params(self, mocker):
        cache = OurOwnCache()
        cache.configure(FakeBackend(), app="worker")
        assert cache._app == "worker"
        sample_function = RandomCounter().async_call_function
        cached_function = cache.cache_function()(sample_function)
        assert (await cached_function()) == 8
        assert (await cached_function()) == 8
        assert (await cached_function()) == 8

    @pytest.mark.asyncio
    async def test_simple_caching_fake_backend_async_with_params(self, mocker):
        mock_log = mocker.patch.object(cache_log, "info")
        log_map = LogMapping(
            {
                "args_indexes_to_log": [0, 1],
                "kwargs_keys_to_log": ["base", "head", "something"],
            }
        )
        cache = OurOwnCache()
        cache.configure(FakeBackend())
        assert cache._app == "shared"
        sample_function = RandomCounter().async_call_function_args
        cached_function = cache.cache_function(log_hits=True, log_map=log_map)(
            sample_function
        )
        assert await cached_function("base", "head", something="batata") == "basehead"
        mock_log.assert_not_called()  # not a hit, not logger
        assert await cached_function("base", "head", something="else") == "basehead"
        mock_log.assert_not_called()  # not a hit, not logger
        assert await cached_function("base", "head", something="else") == "basehead"
        assert mock_log.call_count == 1
        args, kwargs = mock_log.call_args
        assert args == ("Returning cache hit",)
        assert "extra" in kwargs
        extra_logged = kwargs["extra"]
        extra_args = extra_logged["fn_args"]
        extra_kwargs = extra_logged["fn_kwargs"]
        assert extra_args == ["base", "head"]
        assert extra_kwargs == {
            "something": "else"
        }  # Notice that danger is not part of it
        # Changing the way we call the function
        assert (
            await cached_function("base", head="head", something="else") == "basehead"
        )
        assert mock_log.call_count == 1  # This is not cached because the args changed
        assert (
            await cached_function("base", head="head", something="else") == "basehead"
        )
        assert mock_log.call_count == 2
        args, kwargs = mock_log.call_args
        assert args == ("Returning cache hit",)
        assert "extra" in kwargs
        extra_logged = kwargs["extra"]
        extra_args = extra_logged["fn_args"]
        extra_kwargs = extra_logged["fn_kwargs"]
        assert extra_args == ["base"]
        assert extra_kwargs == {
            "head": "head",
            "something": "else",
        }  # Notice that danger is not part of it

    @pytest.mark.asyncio
    async def test_make_hash_sha256(self):
        assert make_hash_sha256(1) == "a4ayc/80/OGda4BO/1o/V0etpOqiLx1JwB5S3beHW0s="
        assert (
            make_hash_sha256("somestring")
            == "l5nfZJ7iQAll9QGKjGm4wPuSgUoikOMrdpOw/36GLyw="
        )
        this_set = set(["1", "something", "True", "another_string_of_values"])
        assert (
            make_hash_sha256(this_set) == "siFp5vd4+aI5SxlURDMV3Z5Yfn5qnpSbCctIewE6m44="
        )
        this_set.add("ooops")
        assert (
            make_hash_sha256(this_set) == "aoU2Of3YNk0/iW1hqfSkXPbhIAzGMHCSCoxsiLI2b8U="
        )
