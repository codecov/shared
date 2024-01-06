import os
import sqlite3
import tempfile
from typing import Any, Dict, Iterator, Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.sql import func

from shared.bundle_analysis import models
from shared.bundle_analysis.parser import Parser


class AssetReport:
    """
    Report wrapper around a single asset (many of which can exist in a single bundle).
    """

    def __init__(self, asset: models.Asset):
        self.asset = asset
        self.db_session = SQLAlchemySession.object_session(self.asset)

    @property
    def name(self):
        return self.asset.normalized_name

    @property
    def hashed_name(self):
        return self.asset.name

    @property
    def size(self):
        return self.asset.size

    def modules(self):
        return (
            self.db_session.query(models.Module)
            .join(models.Module.chunks)
            .join(models.Chunk.assets)
            .filter(models.Asset.id == self.asset.id)
            .all()
        )


class BundleReport:
    """
    Report wrapper around a single bundle (many of which can exist in a single analysis report).
    """

    def __init__(self, bundle: models.Bundle):
        self.bundle = bundle
        self.db_session = SQLAlchemySession.object_session(self.bundle)

    @property
    def name(self):
        return self.bundle.name

    def asset_reports(self) -> Iterator[AssetReport]:
        assets = (
            self.db_session.query(models.Asset)
            .join(models.Asset.session)
            .join(models.Session.bundle)
            .filter(models.Bundle.id == self.bundle.id)
            .all()
        )
        return (AssetReport(asset) for asset in assets)

    def total_size(self) -> int:
        return (
            self.db_session.query(func.sum(models.Asset.size).label("asset_size"))
            .join(models.Asset.session)
            .join(models.Session.bundle)
            .filter(models.Session.bundle_id == self.bundle.id)
            .scalar()
        ) or 0


class BundleAnalysisReport:
    """
    Report wrapper around multiple bundles for a single commit report.
    """

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

    def ingest(self, path: str) -> int:
        """
        Ingest the bundle stats JSON at the given file path.
        Returns session ID of ingested data.
        """
        parser = Parser(self.db_session)
        session_id = parser.parse(path)
        self.db_session.commit()
        return session_id

    def metadata(self) -> Dict[models.MetadataKey, Any]:
        metadata = self.db_session.query(models.Metadata).all()
        return {models.MetadataKey(item.key): item.value for item in metadata}

    def bundle_reports(self) -> Iterator[BundleReport]:
        bundles = self.db_session.query(models.Bundle).all()
        return (BundleReport(bundle) for bundle in bundles)

    def bundle_report(self, bundle_name: str) -> Optional[BundleReport]:
        bundle = (
            self.db_session.query(models.Bundle).filter_by(name=bundle_name).first()
        )
        if bundle is None:
            return None
        return BundleReport(bundle)

    def session_count(self) -> int:
        return self.db_session.query(models.Session).count()
