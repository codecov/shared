import logging

from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server

log = logging.getLogger(__name__)

start_prometheus = start_http_server


__all__ = [
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "start_prometheus",
]


def inc_counter(counter: Counter, labels: dict | None = None) -> None:
    try:
        if labels:
            counter.labels(**labels).inc()
        else:
            counter.inc()
    except Exception as e:
        log.warning(f"Error incrementing counter {counter._name}: {e}")


def set_gauge(gauge: Gauge, value, labels: dict | None = None) -> None:
    try:
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)
    except Exception as e:
        log.warning(f"Error setting gauge {gauge._name}: {e}")
