import json
import logging
import os
import sqlite3
import tempfile
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import sentry_sdk
from sqlalchemy import asc, desc, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import func
from sqlalchemy.sql.functions import coalesce

from shared.bundle_analysis.db_migrations import BundleAnalysisMigration
from shared.bundle_analysis.models import (
    SCHEMA,
    SCHEMA_VERSION,
    Asset,
    AssetType,
    Bundle,
    Chunk,
    Metadata,
    MetadataKey,
    Module,
    Session,
    get_db_session,
)
from shared.bundle_analysis.parser import Parser

log = logging.getLogger(__name__)


class ModuleReport:
    """
    Report wrapper around a single module (many of which can exist in a single Asset via Chunks)
    """

    def __init__(self, db_path: str, module: Module):
        self.db_path = db_path
        self.module = module

    @property
    def name(self):
        return self.module.name

    @property
    def size(self):
        return self.module.size


class AssetReport:
    """
    Report wrapper around a single asset (many of which can exist in a single bundle).
    """

    def __init__(self, db_path: str, asset: Asset):
        self.db_path = db_path
        self.asset = asset

    @property
    def id(self):
        return self.asset.id

    @property
    def name(self):
        return self.asset.normalized_name

    @property
    def hashed_name(self):
        return self.asset.name

    @property
    def size(self):
        return self.asset.size

    @property
    def gzip_size(self):
        return self.asset.gzip_size

    @property
    def uuid(self):
        return self.asset.uuid

    @property
    def asset_type(self):
        return self.asset.asset_type

    def modules(self):
        with get_db_session(self.db_path) as session:
            modules = (
                session.query(Module)
                .join(Module.chunks)
                .join(Chunk.assets)
                .filter(Asset.id == self.asset.id)
                .all()
            )
            return [ModuleReport(self.db_path, module) for module in modules]


class BundleReport:
    """
    Report wrapper around a single bundle (many of which can exist in a single analysis report).
    """

    def __init__(self, db_path: str, bundle: Bundle):
        self.db_path = db_path
        self.bundle = bundle

    @property
    def name(self):
        return self.bundle.name

    def _asset_filter(
        self,
        query: Query,
        asset_types: Optional[List[AssetType]] = None,
        chunk_entry: Optional[bool] = None,
        chunk_initial: Optional[bool] = None,
    ) -> Query:
        # Filter in assets having chunks with requested initial value
        if chunk_initial is not None:
            query = query.join(Asset.chunks).filter(Chunk.initial == chunk_initial)
        # Filter in assets having chunks with requested entry value
        if chunk_entry is not None:
            query = query.join(Asset.chunks).filter(Chunk.entry == chunk_entry)
        # Filter in assets belonging to requested asset types
        if asset_types is not None:
            query = query.filter(Asset.asset_type.in_(asset_types))
        return query

    @sentry_sdk.trace
    def asset_reports(
        self,
        asset_types: Optional[List[AssetType]] = None,
        chunk_entry: Optional[bool] = None,
        chunk_initial: Optional[bool] = None,
        ordering_column: str = "size",
        ordering_desc: Optional[bool] = True,
    ) -> Iterator[AssetReport]:
        with get_db_session(self.db_path) as session:
            ordering = desc if ordering_desc else asc
            assets = (
                session.query(Asset)
                .join(Asset.session)
                .join(Session.bundle)
                .filter(Bundle.id == self.bundle.id)
            )
            assets = self._asset_filter(
                assets,
                asset_types,
                chunk_entry,
                chunk_initial,
            ).order_by(ordering(getattr(Asset, ordering_column)))
            return (AssetReport(self.db_path, asset) for asset in assets.all())

    def total_size(
        self,
        asset_types: Optional[List[AssetType]] = None,
        chunk_entry: Optional[bool] = None,
        chunk_initial: Optional[bool] = None,
    ) -> int:
        with get_db_session(self.db_path) as session:
            assets = (
                session.query(func.sum(Asset.size).label("asset_size"))
                .join(Asset.session)
                .join(Session.bundle)
                .filter(Bundle.id == self.bundle.id)
            )
            assets = self._asset_filter(
                assets,
                asset_types,
                chunk_entry,
                chunk_initial,
            )
            return assets.scalar() or 0

    def total_gzip_size(
        self,
        asset_types: Optional[List[AssetType]] = None,
        chunk_entry: Optional[bool] = None,
        chunk_initial: Optional[bool] = None,
    ) -> int:
        """
        Returns the sum of all assets' gzip_size if present plus
        the sum of all assets' size if they do not have gzip_size value.
        This simulates the amount of data transfer in a realistic setting,
        for those assets that are not compressible we will use its uncompressed size.
        """
        with get_db_session(self.db_path) as session:
            assets = (
                session.query(
                    func.sum(coalesce(Asset.gzip_size, Asset.size)).label("size")
                )
                .join(Asset.session)
                .join(Session.bundle)
                .filter(Bundle.id == self.bundle.id)
            )
            assets = self._asset_filter(
                assets,
                asset_types,
                chunk_entry,
                chunk_initial,
            )
            return assets.scalar() or 0

    def info(self) -> dict:
        with get_db_session(self.db_path) as session:
            result = (
                session.query(Session)
                .filter(Session.bundle_id == self.bundle.id)
                .first()
            )
            return json.loads(result.info)

    def is_cached(self) -> bool:
        with get_db_session(self.db_path) as session:
            result = session.query(Bundle).filter(Bundle.id == self.bundle.id).first()
            return result.is_cached


class BundleAnalysisReport:
    """
    Report wrapper around multiple bundles for a single commit report.
    """

    db_path: str

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            _, self.db_path = tempfile.mkstemp(prefix="bundle_analysis_")
        else:
            self.db_path = db_path
        with get_db_session(self.db_path) as db_session:
            self._setup(db_session)

    @sentry_sdk.trace
    def _setup(self, db_session: DbSession) -> None:
        """
        Creates the schema for a new bundle report database.
        """
        try:
            schema_version = (
                db_session.query(Metadata)
                .filter_by(key=MetadataKey.SCHEMA_VERSION.value)
                .first()
            ).value
            if schema_version < SCHEMA_VERSION:
                log.info(
                    f"Migrating Bundle Analysis DB schema from {schema_version} to {SCHEMA_VERSION}"
                )
                BundleAnalysisMigration(
                    db_session, schema_version, SCHEMA_VERSION
                ).migrate()
        except OperationalError:
            # schema does not exist
            try:
                con = sqlite3.connect(self.db_path)
                con.executescript(SCHEMA)
                con.commit()
            finally:
                con.close()
            schema_version = Metadata(
                key=MetadataKey.SCHEMA_VERSION.value,
                value=SCHEMA_VERSION,
            )
            db_session.add(schema_version)
            db_session.commit()

    def cleanup(self):
        os.unlink(self.db_path)

    @sentry_sdk.trace
    def ingest(self, path: str, compare_sha: Optional[str] = None) -> Tuple[int, str]:
        """
        Ingest the bundle stats JSON at the given file path.
        Returns session ID of ingested data.
        """
        with get_db_session(self.db_path) as session:
            # Normally Assets/Chunks/Modules are cascade deleted and the many-to-many table entries
            # would be deleted as well as they are foreign keys. However some rare cases occurs
            # where the chunks_modules and assets_chunks table IDs doesn't exist in its
            # associated Assets/Chunks/Modules table even though they are foreign keys.
            # Fix: before each ingestion we make sure these rows are deleted.
            for params in [
                ["chunks_modules", "chunk_id", "chunks", "module_id", "modules"],
                ["assets_chunks", "asset_id", "assets", "chunk_id", "chunks"],
            ]:
                sql = text(
                    f"""
                    DELETE FROM {params[0]}
                    WHERE
                        {params[1]} NOT IN (SELECT id FROM {params[2]})
                        OR {params[3]} NOT IN (SELECT id FROM {params[4]})
                """
                )
                result = session.execute(sql)
                session.commit()
                rows_deleted = result.rowcount
                if rows_deleted > 0:
                    log.warning(
                        f"Integrity error detected, deleted {rows_deleted} corrupted rows from {params[0]}"
                    )

            parser = Parser(path, session).get_proper_parser()
            session_id, bundle_name = parser.parse(path)

            # Save custom base commit SHA for doing comparisons if available
            if compare_sha:
                sql = text(
                    """
                    INSERT OR REPLACE INTO metadata (key, value)
                    VALUES (:key, :value)
                """
                )
                session.execute(
                    sql, {"key": "compare_sha", "value": json.dumps(compare_sha)}
                )
                session.commit()

            session.commit()
            return session_id, bundle_name

    def _associate_bundle_report_assets_by_name(
        self, curr_bundle_report: BundleReport, prev_bundle_report: BundleReport
    ) -> Set[Tuple[str, str]]:
        """
        Rule 1
        Returns a set of pairs of UUIDs (the current asset UUID and prev asset UUID)
        representing that the curr asset UUID should be updated to the prev asset UUID
        because the curr asset has the same hashed name as the previous asset
        """
        ret = set()
        prev_asset_hashed_names = {
            a.hashed_name: a.uuid for a in prev_bundle_report.asset_reports()
        }
        for curr_asset in curr_bundle_report.asset_reports():
            if curr_asset.asset_type == AssetType.JAVASCRIPT:
                if curr_asset.hashed_name in prev_asset_hashed_names:
                    ret.add(
                        (
                            prev_asset_hashed_names[curr_asset.hashed_name],
                            curr_asset.uuid,
                        )
                    )
        return ret

    def _associate_bundle_report_assets_by_module_names(
        self, curr_bundle_report: BundleReport, prev_bundle_report: BundleReport
    ) -> Set[Tuple[str, str]]:
        """
        Rule 2
        Returns a set of pairs of UUIDs (the current asset UUID and prev asset UUID)
        representing that the curr asset UUID should be updated to the prev asset UUID
        because there exists a prev asset where all its module names are the same as the
        curr asset module names
        """
        ret = set()
        prev_module_asset_mapping = {}
        for prev_asset in prev_bundle_report.asset_reports():
            if prev_asset.asset_type == AssetType.JAVASCRIPT:
                prev_modules = tuple(
                    sorted(frozenset([m.name for m in prev_asset.modules()]))
                )
                # NOTE: Assume two non-related assets CANNOT have the same set of modules
                # though in reality there can be rare cases of this but we
                # will deal with that later if it becomes a prevalent problem
                prev_module_asset_mapping[prev_modules] = prev_asset.uuid

        for curr_asset in curr_bundle_report.asset_reports():
            if curr_asset.asset_type == AssetType.JAVASCRIPT:
                curr_modules = tuple(
                    sorted(frozenset([m.name for m in curr_asset.modules()]))
                )
                if curr_modules in prev_module_asset_mapping:
                    ret.add(
                        (
                            prev_module_asset_mapping[curr_modules],
                            curr_asset.uuid,
                        )
                    )
        return ret

    @sentry_sdk.trace
    def associate_previous_assets(
        self, prev_bundle_analysis_report: "BundleAnalysisReport"
    ) -> None:
        """
        Only associate past asset if it is Javascript or Typescript types
        and belonging to the same bundle name
        Associated if one of the following is true
        Rule 1. Previous and current asset have the same hashed name
        Rule 2. Previous and current asset shared the same set of module names
        """
        associated_assets_found = set()

        prev_bundle_reports = list(prev_bundle_analysis_report.bundle_reports())
        for curr_bundle_report in self.bundle_reports():
            for prev_bundle_report in prev_bundle_reports:
                if curr_bundle_report.name == prev_bundle_report.name:
                    # Rule 1 check
                    associated_assets_found |= (
                        self._associate_bundle_report_assets_by_name(
                            curr_bundle_report, prev_bundle_report
                        )
                    )

                    # Rule 2 check
                    associated_assets_found |= (
                        self._associate_bundle_report_assets_by_module_names(
                            curr_bundle_report, prev_bundle_report
                        )
                    )

        with get_db_session(self.db_path) as session:
            # Update the Assets table for the bundle correct uuid
            for pair in associated_assets_found:
                prev_uuid, curr_uuid = pair
                session.query(Asset).filter(Asset.uuid == curr_uuid).update(
                    {Asset.uuid: prev_uuid}
                )
            session.commit()

    def metadata(self) -> Dict[MetadataKey, Any]:
        with get_db_session(self.db_path) as session:
            metadata = session.query(Metadata).all()
            return {MetadataKey(item.key): item.value for item in metadata}

    def bundle_reports(self) -> Iterator[BundleReport]:
        with get_db_session(self.db_path) as session:
            bundles = session.query(Bundle).all()
            return (BundleReport(self.db_path, bundle) for bundle in bundles)

    def bundle_report(self, bundle_name: str) -> Optional[BundleReport]:
        with get_db_session(self.db_path) as session:
            bundle = session.query(Bundle).filter_by(name=bundle_name).first()
            if bundle is None:
                return None
            return BundleReport(self.db_path, bundle)

    def session_count(self) -> int:
        with get_db_session(self.db_path) as session:
            return session.query(Session).count()

    def update_is_cached(self, data: Dict[str, bool]) -> None:
        with get_db_session(self.db_path) as session:
            for bundle_name, value in data.items():
                session.query(Bundle).filter(Bundle.name == bundle_name).update(
                    {Bundle.is_cached: value}
                )
            session.commit()

    def is_cached(self) -> bool:
        with get_db_session(self.db_path) as session:
            cached_bundles = session.query(Bundle).filter_by(is_cached=True)
            return cached_bundles.count() > 0

    @sentry_sdk.trace
    def delete_bundle_by_name(self, bundle_name: str) -> None:
        with get_db_session(self.db_path) as session:
            bundle_to_be_deleted = (
                session.query(Bundle).filter_by(name=bundle_name).one_or_none()
            )
            if bundle_to_be_deleted is None:
                return

            # Deletes Asset, Chunk, Module
            session_to_be_deleted = (
                session.query(Session)
                .filter(Session.bundle == bundle_to_be_deleted)
                .one_or_none()
            )
            if session_to_be_deleted is None:
                raise Exception(
                    "Data integrity error - cannot have Bundles without Sessions"
                )
            for model in [Asset, Chunk, Module]:
                stmt = model.__table__.delete().where(
                    model.session == session_to_be_deleted
                )
                session.execute(stmt)

            # Deletes Session and Bundle
            session.delete(session_to_be_deleted)
            session.delete(bundle_to_be_deleted)

            session.commit()
