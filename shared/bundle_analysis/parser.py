import json
from typing import Optional, Tuple

import ijson
from sqlalchemy.orm import Session as DbSession

from shared.bundle_analysis.models import (
    SCHEMA,
    Asset,
    Bundle,
    Chunk,
    Module,
    Session,
    assets_chunks,
    chunks_modules,
)


class Parser:
    """
    This does a streaming JSON parse of the stats JSON file referenced by `path`.
    It's more complicated that just doing a `json.loads` but should keep our memory
    usage constrained.
    """

    def __init__(self, db_session: DbSession):
        self.db_session = db_session

    def reset(self):
        """
        Resets temporary parser state in order to parse a new file path.
        """
        # asset name -> asset id
        self.asset_index = {}

        # chunk external id -> chunk internal id
        self.chunk_index = {}

        # chunk id -> asset name list
        self.chunk_asset_names_index = {}

        # module id -> chunk external id list
        self.module_chunk_unique_external_ids_index = {}

        # misc. top-level info from the stats data (i.e. bundler version, bundle time, etc.)
        self.info = {}

        # temporary parser state
        self.session = None
        self.asset = None
        self.chunk = None
        self.chunk_asset_names = []
        self.module = None
        self.module_chunk_unique_external_ids = []

    def parse(self, path: str) -> int:
        try:
            self.reset()

            # Retrieve the info section first before parsing all the other things
            # this way when an error is raised we know which bundle plugin caused it
            with open(path, "rb") as f:
                for event in ijson.parse(f):
                    self._parse_info(event)

            self.session = Session(info={})
            self.db_session.add(self.session)

            with open(path, "rb") as f:
                for event in ijson.parse(f):
                    self._parse_event(event)

                # Delete old session/asset/chunk/module with the same bundle name if applicable
                old_session = (
                    self.db_session.query(Session)
                    .filter(
                        Session.bundle == self.session.bundle,
                        Session.id != self.session.id,
                    )
                    .one_or_none()
                )
                if old_session:
                    for model in [Asset, Chunk, Module]:
                        to_be_deleted = self.db_session.query(model).filter(
                            model.session == old_session
                        )
                        for item in to_be_deleted:
                            self.db_session.delete(item)
                            self.db_session.flush()
                    self.db_session.delete(old_session)
                    self.db_session.flush()

                # save top level bundle stats info
                self.session.info = json.dumps(self.info)

                # this happens last so that we could potentially handle any ordering
                # of top-level keys inside the JSON (i.e. we couldn't associate a chunk
                # to an asset above if we parse the chunk before the asset)
                self._create_associations()

                assert self.session.bundle is not None
                return self.session.id
        except Exception as e:
            # Inject the plugin name to the Exception object so we have visibilitity on which plugin
            # is causing the trouble.
            e.bundle_analysis_plugin_name = self.info.get("plugin_name", "unknown")
            raise e

    def _parse_info(self, event: Tuple[str, str, str]):
        prefix, _, value = event

        # session info
        if prefix == "version":
            self.info["version"] = value
        elif prefix == "bundler.name":
            self.info["bundler_name"] = value
        elif prefix == "bundler.version":
            self.info["bundler_version"] = value
        elif prefix == "builtAt":
            self.info["built_at"] = value
        elif prefix == "plugin.name":
            self.info["plugin_name"] = value
        elif prefix == "plugin.version":
            self.info["plugin_version"] = value
        elif prefix == "duration":
            self.info["duration"] = value

    def _parse_event(self, event: Tuple[str, str, str]):
        prefix, _, value = event
        prefix_path = prefix.split(".")

        # asset / chunks / modules
        if prefix_path[0] == "assets":
            self._parse_assets_event(*event)
        elif prefix_path[0] == "chunks":
            self._parse_chunks_event(*event)
        elif prefix_path[0] == "modules":
            self._parse_modules_event(*event)

        # bundle name
        elif prefix == "bundleName":
            bundle = self.db_session.query(Bundle).filter_by(name=value).first()
            if bundle is None:
                bundle = Bundle(name=value)
                self.db_session.add(bundle)
            self.session.bundle = bundle
            self.db_session.flush()

    def _parse_assets_event(self, prefix: str, event: str, value: str):
        if (prefix, event) == ("assets.item", "start_map"):
            # new asset
            assert self.asset is None
            self.asset = Asset(session=self.session)
        elif prefix == "assets.item.name":
            self.asset.name = value
        elif prefix == "assets.item.normalized":
            self.asset.normalized_name = value
        elif prefix == "assets.item.size":
            self.asset.size = int(value)
        elif (prefix, event) == ("assets.item", "end_map"):
            # save asset
            self.db_session.add(self.asset)
            self.db_session.flush()
            self.asset_index[self.asset.name] = self.asset.id
            # reset parser state
            self.asset = None

    def _parse_chunks_event(self, prefix: str, event: str, value: str):
        if (prefix, event) == ("chunks.item", "start_map"):
            # new chunk
            assert self.chunk is None
            self.chunk = Chunk(session=self.session)
        elif prefix == "chunks.item.id":
            self.chunk.external_id = value
        elif prefix == "chunks.item.uniqueId":
            self.chunk.unique_external_id = value
        elif prefix == "chunks.item.initial":
            self.chunk.initial = value
        elif prefix == "chunks.item.entry":
            self.chunk.entry = value
        elif prefix == "chunks.item.files.item":
            self.chunk_asset_names.append(value)
        elif (prefix, event) == ("chunks.item", "end_map"):
            # save chunk
            self.db_session.add(self.chunk)
            self.db_session.flush()
            self.chunk_index[self.chunk.external_id] = self.chunk.id
            self.chunk_asset_names_index[self.chunk.id] = self.chunk_asset_names
            # reset parser state
            self.chunk = None
            self.chunk_asset_names = []

    def _parse_modules_event(self, prefix: str, event: str, value: str):
        if (prefix, event) == ("modules.item", "start_map"):
            # new module
            assert self.module is None
            self.module = Module(session=self.session)
        elif prefix == "modules.item.name":
            self.module.name = value
        elif prefix == "modules.item.size":
            self.module.size = int(value)
        elif prefix == "modules.item.chunkUniqueIds.item":
            self.module_chunk_unique_external_ids.append(value)
        elif (prefix, event) == ("modules.item", "end_map"):
            # save module
            self.db_session.add(self.module)
            self.db_session.flush()
            self.module_chunk_unique_external_ids_index[
                self.module.id
            ] = self.module_chunk_unique_external_ids
            # reset parser state
            self.module = None
            self.module_chunk_unique_external_ids = []

    def _create_associations(self):
        # associate chunks to assets
        inserts = []
        for chunk_id, asset_names in self.chunk_asset_names_index.items():
            assets = self.db_session.query(Asset).filter(
                Asset.session == self.session,
                Asset.name.in_(asset_names),
            )
            inserts.extend(
                [dict(asset_id=asset.id, chunk_id=chunk_id) for asset in assets]
            )
        if inserts:
            self.db_session.execute(assets_chunks.insert(), inserts)

        # associate modules to chunks
        # FIXME: this isn't quite right - need to sort out how non-JS assets reference chunks
        inserts = []
        for (
            module_id,
            chunk_unique_external_ids,
        ) in self.module_chunk_unique_external_ids_index.items():
            chunks = self.db_session.query(Chunk).filter(
                Chunk.session == self.session,
                Chunk.unique_external_id.in_(chunk_unique_external_ids),
            )
            inserts.extend(
                [dict(chunk_id=chunk.id, module_id=module_id) for chunk in chunks]
            )
        if inserts:
            self.db_session.execute(chunks_modules.insert(), inserts)
