import json
import logging

from google.auth.exceptions import GoogleAuthError
from google.cloud import pubsub_v1

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Event
from shared.config import get_config

log = logging.getLogger("__name__")


class PubSub(BaseAnalyticsTool):
    def __init__(
        self,
        batch_max_bytes: int = 1024 * 1024 * 5,
        batch_max_latency: float = 0.05,
        batch_max_messages: int = 1000,
    ) -> None:
        settings = pubsub_v1.types.BatchSettings(
            max_bytes=batch_max_bytes,
            max_latency=batch_max_latency,
            max_messages=batch_max_messages,
        )
        self.project = get_config("setup", "pubsub", "project_id")
        topic_name = get_config("setup", "pubsub", "topic")
        self.publisher = self.get_publisher(settings)
        if self.publisher:
            self.topic = self.publisher.topic_path(self.project, topic_name)

    @classmethod
    def is_enabled(cls):
        return bool(get_config("setup", "pubsub", "enabled", default=False))

    def get_publisher(self, settings):
        if not self.is_enabled():
            return None
        try:
            publisher = pubsub_v1.PublisherClient(settings)
        except GoogleAuthError:
            log.warning("Unable to initialize PubSub, no auth found")
            publisher = None
        return publisher

    def track_event(self, event: Event, *, is_enterprise=False, context=None):
        if is_enterprise:
            return
        if self.publisher is not None:
            self.publisher.publish(
                self.topic, data=json.dumps(event.serialize()).encode("utf-8")
            )
