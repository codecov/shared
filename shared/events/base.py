from abc import ABC, abstractmethod


class EventPublisherPropertyException(Exception):
    pass


class EventPublisher[T, P](ABC):
    @abstractmethod
    def publish(self, event_type: T, event_properties: P):
        pass
