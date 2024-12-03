import logging

import ijson
from sqlalchemy.orm import Session as DbSession

from shared.bundle_analysis.parsers import ParserInterface, ParserV1, ParserV2, ParserV3
from shared.bundle_analysis.parsers.base import ParserTrait

log = logging.getLogger(__name__)


PARSER_VERSION_MAPPING: dict[str, type[ParserTrait]] = {
    "1": ParserV1,
    "2": ParserV2,
    "3": ParserV3,
}


class Parser:
    """
    # Retrieve bundle stats file version and return an associated instance of its parser
    """

    def __init__(self, path: str, db_session: DbSession):
        self.path = path
        self.db_session = db_session

    def get_proper_parser(self) -> ParserTrait:
        error = None
        try:
            with open(self.path, "rb") as f:
                for event in ijson.parse(f):
                    prefix, _, value = event
                    if prefix == "version":
                        selected_parser = PARSER_VERSION_MAPPING.get(value)
                        if selected_parser is None:
                            error = f"parser not implemented for version {value}"
                        elif not issubclass(selected_parser, ParserInterface):
                            error = "invalid parser implementation"
                        else:
                            return selected_parser(self.db_session)
            error = "version does not exist in bundle file"
        except IOError:
            error = "unable to open file"
        if error:
            raise Exception(f"Couldn't parse bundle: {error}")
        raise Exception("Couldn't parse bundle: unknown error")
