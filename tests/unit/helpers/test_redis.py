from shared.helpers.redis import get_redis_url


def test_get_redis_default():
    assert get_redis_url() == "redis://redis:6379"


def test_get_redis_from_url(mock_configuration):
    mock_configuration.set_params(
        {"services": {"redis_url": "https://my-redis-instance:6378"}}
    )
    assert get_redis_url() == "https://my-redis-instance:6378"
