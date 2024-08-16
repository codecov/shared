from shared.config import get_config


def is_timeseries_enabled() -> bool:
    return get_config("setup", "timeseries", "enabled", default=False)
