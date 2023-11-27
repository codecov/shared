import os
import re
import sqlite3
import tempfile
from typing import Any, Dict, Iterator, Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from . import models
from .parser import parse

# matches file paths with content hashes like:
# path/to/file-aa21a697.ext
CONTENT_HASH_RE = re.compile(r"^.+(-[\w\d]{8})\.[\w\d]+$")


class Bundle:
    def __init__(self, asset: models.Asset):
        self.asset = asset
        self.db_session = Session.object_session(self.asset)

    @property
    def name(self):
        return self.asset.name

    @property
    def size(self):
        return self.asset.size

    @property
    def id(self):
        """
        Attempts to track the unique name of the bundle while ignoring
        content hashes found in the file name.

        For example, if the name is `path/to/file-aa21a697.ext` then this
        method will return `path/to/file.ext`
        """
        res = self.name

        # FIXME: this is likely too naive to work in all cases - need to figure out
        # various ways these content hashes can be formed
        re_match = CONTENT_HASH_RE.match(self.name)
        if re_match:
            (dash_hash,) = re_match.groups()
            res = self.name.replace(dash_hash, "")

        return res

    def modules(self):
        return (
            self.db_session.query(models.Module)
            .join(models.Module.chunks)
            .join(models.Chunk.assets)
            .filter(models.Asset.id == self.asset.id)
            .all()
        )


class BundleReport:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        if self.db_path is None:
            _, self.db_path = tempfile.mkstemp()
        self.db_session = models.get_db_session(self.db_path)
        self._setup()

    def _setup(self):
        """
        Creates the schema for a new bundle report database.
        """
        try:
            schema_version = (
                self.db_session.query(models.Metadata)
                .filter_by(key=models.MetadataKey.SCHEMA_VERSION.value)
                .first()
            )
            self._migrate(schema_version.value)
        except OperationalError:
            # schema does not exist
            con = sqlite3.connect(self.db_path)
            con.executescript(models.SCHEMA)
            schema_version = models.Metadata(
                key=models.MetadataKey.SCHEMA_VERSION.value,
                value=models.SCHEMA_VERSION,
            )
            self.db_session.add(schema_version)
            self.db_session.commit()

    def _migrate(self, schema_version: int):
        """
        Migrate the database from `schema_version` to `models.SCHEMA_VERSION`
        such that the resulting schema is identical to `models.SCHEMA`
        """
        # we don't have any migrations yet
        assert schema_version == models.SCHEMA_VERSION

    def cleanup(self):
        self.db_session.close()
        os.unlink(self.db_path)

    def ingest(self, path: str):
        """
        Ingest the bundle stats JSON at the given file path.
        """
        parse(self.db_session, path)
        self.db_session.commit()

    def metadata(self) -> Dict[models.MetadataKey, Any]:
        metadata = self.db_session.query(models.Metadata).all()
        return {models.MetadataKey(item.key): item.value for item in metadata}

    def bundles(self) -> Iterator[Bundle]:
        assets = self.db_session.query(models.Asset).all()
        return (Bundle(asset) for asset in assets)

    def total_size(self) -> int:
        return self.db_session.query(
            func.sum(models.Asset.size).label("asset_size")
        ).scalar()
