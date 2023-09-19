from datetime import datetime

import pytz

epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)


def to_timestamp(value: datetime) -> float:
    """
    Convert a time zone aware datetime to a POSIX timestamp (with fractional
    component.)
    """
    return (value - epoch).total_seconds()
