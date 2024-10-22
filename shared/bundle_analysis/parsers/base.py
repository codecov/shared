import abc
from typing import Tuple

from sqlalchemy.orm import Session


class ParserInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, "parse") and callable(subclass.parse)


class ParserTrait:
    @abc.abstractmethod
    def __init__(self, db_session: Session):
        pass

    @abc.abstractmethod
    def parse(self, path: str) -> Tuple[int, str]:
        pass
