import logging
from typing import Optional

import ijson
from sqlalchemy.orm import Session as DbSession

from shared.bundle_analysis.parsers import ParserV1, ParserV2

log = logging.getLogger(__name__)


PARSER_VERSION_MAPPING = {
    "1": ParserV1,
    "2": ParserV2,
}


class Parser:
    """
    # Retrieve bundle stats file version and return an associated instance of its parser
    """

    def __new__(cls, path: str, db_session: DbSession) -> Optional[object]:
        with open(path, "rb") as f:
            for event in ijson.parse(f):
                prefix, _, value = event
                if prefix == "version":
                    return PARSER_VERSION_MAPPING[value](db_session)
