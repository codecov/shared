from prometheus_client import Counter, Histogram, Summary, start_http_server
from statsd.defaults.env import statsd

metrics = statsd

start_prometheus = start_http_server
