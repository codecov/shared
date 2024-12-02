import asyncio
import base64
import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Hashable, List, Optional

from redis import Redis, RedisError

log = logging.getLogger(__name__)

NO_VALUE = object()

DEFAULT_TTL = 120


def attempt_json_dumps(value: Any) -> str:
    def assert_string_keys(d: dict[Any, Any]) -> None:
        for k, v in d.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"Attempted to JSON-serialize a dictionary with non-string key: {k}"
                )
            if isinstance(v, dict):
                assert_string_keys(v)

    if isinstance(value, dict):
        assert_string_keys(value)

    return json.dumps(value)


def make_hash_sha256(o: Any) -> str:
    """Provides a machine-independent, consistent hash value for any object

    Args:
        o (Any): Any object we want

    Returns:
        str: a sha256-based hash that is always the same for the same object
    """
    hasher = hashlib.sha256()
    hasher.update(repr(make_hashable(o)).encode())
    return base64.b64encode(hasher.digest()).decode()


def make_hashable(o: Any) -> Hashable:
    """
    Converts any object into an object that will have a consistent hash
    """
    if isinstance(o, (tuple, list)):
        return tuple((make_hashable(e) for e in o))
    if isinstance(o, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in o.items()))
    if isinstance(o, (set, frozenset)):
        return tuple(sorted(make_hashable(e) for e in o))
    return o


class BaseBackend(object):
    """
    This is the interface a class needs to honor in order to work as a backend.

    The only two needed functions are `get` and `set`, which will fetch information from the
        cache and send information to it, respectively.

    However the cache wants to work internally, it's their choice. They only need to be able to
        `set` and `get` without raising any exceptions
    """

    def get(self, key: str) -> Any:
        """Returns a cached value from the cache, or NO_VALUE, if no cache is set for that key

        Args:
            key (str): The key that represents the objecr

        Returns:
            Any: The object that is possibly cached, or NO_VALUE, if no cache was there
        """
        raise NotImplementedError()

    def set(self, key: str, ttl: int, value: Any):
        raise NotImplementedError()


class NullBackend(BaseBackend):
    """
    This is the default implementation of BaseBackend that is used.

    It essentially `gets` as if nothing is cached, and does not cache anything when requested
        to.

    This makes the cache virtually transparent. It acts as if no cache was there
    """

    def get(self, key: str) -> Any:
        return NO_VALUE

    def set(self, key: str, ttl: int, value: Any):
        pass


class RedisBackend(BaseBackend):
    def __init__(self, redis_connection: Redis):
        self.redis_connection = redis_connection

    def get(self, key: str) -> Any:
        try:
            serialized_value = self.redis_connection.get(key)
        except RedisError:
            log.warning("Unable to fetch from cache on redis", exc_info=True)
            return NO_VALUE
        if serialized_value is None:
            return NO_VALUE
        try:
            return json.loads(serialized_value)
        except ValueError:
            return NO_VALUE

    def set(self, key: str, ttl: int, value: Any):
        try:
            serialized_value = attempt_json_dumps(value)
            self.redis_connection.setex(key, ttl, serialized_value)
        except RedisError:
            log.warning("Unable to set cache on redis", exc_info=True)
        except TypeError:
            log.exception(
                f"Attempted to cache a type that is not JSON-serializable: {value}"
            )


class LogMapping(dict):
    """This let cached functions to specify what arguments they want to log.
    In some cases we want to log cache hits for debugging purposes,
    but some of the arguments might be dangerous to log (e.g. tokens)
    """

    @property
    def args_indexes_to_log(self) -> List[int]:
        """List of args from the function to be logged (if present)"""
        return self.get("args_indexes_to_log", [])

    @property
    def kwargs_keys_to_log(self) -> List[Any]:
        """List of args from the function to be logged (if present)"""
        return self.get("kwargs_keys_to_log", [])


class OurOwnCache(object):
    """
    This is codecov distributed cache's implementation.

    The tldr to use it is, given a function f:

    ```
    from helpers.cache import cache

    @cache.cache_function()
    def f(...):
        ...
    ```

    Now to explain its internal workings.

    This is a configurable-at-runtime cache. Its whole idea is based on the fact that it does
        not need information at import-time. This allows us to use it transparently and still
        not have to change tests, for example, due to it. All tests occur as if the cache was
        not there.

    All that is needed to configure the backend is to do

    ```
    cache.configure(any_backend)
    ```

    which we currently do at `worker_process_init` time with a RedisBackend instance. Other
        instances can be plugged in easily, once needed. A backend is any implementation
        of `BaseBackend`, which is described at their docstrings.

    When `cache.cache_function()` is called, a `FunctionCacher` is returned. They do the heavy
        lifting of actually decorating the function properly, dealign with sync-async context.

    """

    def __init__(self):
        self._backend = NullBackend()
        self._app = "not_configured"

    def configure(self, backend: BaseBackend, app: Optional[str] = None):
        self._backend = backend
        self._app = app or "shared"

    def get_backend(self) -> BaseBackend:
        return self._backend

    def cache_function(
        self,
        ttl: int = DEFAULT_TTL,
        log_hits: bool = False,
        log_map: LogMapping | None = None,
    ) -> "FunctionCacher":
        """Creates a FunctionCacher with all the needed configuration to cache a function

        Args:
            ttl (int, optional): The time-to-live of the cache

        Returns:
            FunctionCacher: A FunctionCacher that can decorate any callable
        """
        return FunctionCacher(
            self, ttl, log_hits, LogMapping(log_map if log_map is not None else {})
        )


class FunctionCacher(object):
    def __init__(
        self, cache_instance: OurOwnCache, ttl: int, log_hits: bool, log_map: LogMapping
    ):
        self.cache_instance = cache_instance
        self.ttl = ttl
        self.log_hits = log_hits
        self.log_map = log_map

    def __call__(self, func) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return self.cache_async_function(func)
        return self.cache_synchronous_function(func)

    def _log_hits(self, func, args, kwargs, key) -> None:
        args_to_log = [
            args[idx] for idx in self.log_map.args_indexes_to_log if idx < len(args)
        ]
        kwargs_to_log = {}
        for lkey in self.log_map.kwargs_keys_to_log:
            if lkey in kwargs:
                kwargs_to_log[lkey] = kwargs[lkey]
        log.info(
            "Returning cache hit",
            extra=dict(
                func=func, fn_args=args_to_log, fn_kwargs=kwargs_to_log, key=key
            ),
        )

    def cache_synchronous_function(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapped(*args, **kwargs):
            key = self.generate_key(func, args, kwargs)
            value = self.cache_instance.get_backend().get(key)
            if value is not NO_VALUE:
                if self.log_hits:
                    self._log_hits(func, args, kwargs, key)
                return value
            result = func(*args, **kwargs)
            self.cache_instance.get_backend().set(key, self.ttl, result)
            return result

        return wrapped

    def generate_key(self, func, args, kwargs) -> str:
        func_name = make_hash_sha256(func.__name__)
        tupled_args = make_hash_sha256(args)
        frozen_kwargs = make_hash_sha256(kwargs)
        return ":".join(["cache", func_name, tupled_args, frozen_kwargs])

    def cache_async_function(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapped(*args, **kwargs):
            key = self.generate_key(func, args, kwargs)
            value = self.cache_instance.get_backend().get(key)
            if value is not NO_VALUE:
                if self.log_hits:
                    self._log_hits(func, args, kwargs, key)
                return value
            result = await func(*args, **kwargs)
            self.cache_instance.get_backend().set(key, self.ttl, result)
            return result

        return wrapped
