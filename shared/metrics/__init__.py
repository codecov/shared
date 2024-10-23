import logging

from prometheus_client import Counter, Histogram, Summary, start_http_server

log = logging.getLogger(__name__)

start_prometheus = start_http_server


__all__ = [
    "Counter",
    "Histogram",
    "Summary",
    "start_prometheus",
]


def inc_counter(counter: Counter, labels: dict = None) -> None:
    try:
        if labels:
            counter.labels(**labels).inc()
        else:
            counter.inc()
    except Exception as e:
        log.warning(f"Error incrementing counter {counter._name}: {e}")
