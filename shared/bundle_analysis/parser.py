import ijson
from sqlalchemy.orm import Session as DbSession

from .models import SCHEMA, Asset, Chunk, Module, Session, assets_chunks, chunks_modules


def parse(db_session: DbSession, path: str):
    """
    This does a streaming JSON parse of the stats JSON file referenced by `path`.
    It's more complicated that just doing a `json.loads` but should keep our memory
    usage constrained.
    """

    session = Session(info={})
    db_session.add(session)

    # this will later get updated with the session once we've
    # parsed all the data
    info = {}

    with open(path, "rb") as f:
        events = ijson.parse(f)

        # asset name -> asset id
        asset_index = {}

        # chunk external id -> chunk internal id
        chunk_index = {}

        # chunk id -> asset name list
        chunk_asset_names_index = {}

        # module id -> chunk external id list
        module_chunk_external_ids_index = {}

        # temporary parser state
        asset = None
        chunk = None
        chunk_asset_names = []
        module = None
        module_chunk_external_ids = []

        for (prefix, event, value) in events:
            # assets
            if (prefix, event) == ("assets.item", "start_map"):
                # new asset
                assert asset is None
                asset = Asset(session=session)
            elif prefix == "assets.item.name":
                asset.name = value
            elif prefix == "assets.item.size":
                asset.size = value
            elif (prefix, event) == ("assets.item", "end_map"):
                # save asset
                db_session.add(asset)
                db_session.flush()
                asset_index[asset.name] = asset.id
                asset = None

            # chunks
            elif (prefix, event) == ("chunks.item", "start_map"):
                # new chunk
                assert chunk is None
                chunk = Chunk()
            elif prefix == "chunks.item.id":
                chunk.external_id = value
            elif prefix == "chunks.item.initial":
                chunk.initial = value
            elif prefix == "chunks.item.entry":
                chunk.entry = value
            elif prefix == "chunks.item.files.item":
                chunk_asset_names.append(value)
            elif (prefix, event) == ("chunks.item", "end_map"):
                # save chunk
                db_session.add(chunk)
                db_session.flush()
                chunk_index[chunk.external_id] = chunk.id
                chunk_asset_names_index[chunk.id] = chunk_asset_names
                chunk = None
                chunk_asset_names = []

            # modules
            elif (prefix, event) == ("modules.item", "start_map"):
                # new module
                assert module is None
                module = Module()
            elif prefix == "modules.item.name":
                module.name = value
            elif prefix == "modules.item.size":
                module.size = value
            elif prefix == "modules.item.chunks.item":
                module_chunk_external_ids.append(value)
            elif (prefix, event) == ("modules.item", "end_map"):
                # save module
                db_session.add(module)
                db_session.flush()
                module_chunk_external_ids_index[module.id] = module_chunk_external_ids
                module = None
                module_chunk_external_ids = []

            # session info
            elif prefix == "version":
                info["version"] = value
            elif prefix == "outputPath":
                info["output_path"] = value
            elif prefix == "bundler.name":
                info["bundler_name"] = value
            elif prefix == "bundler.version":
                info["bundler_version"] = value
            elif prefix == "builtAt":
                info["built_at"] = value

        session.info = info

        # associations
        #   this happens last so that we could potentially handle any ordering
        #   of top-level keys inside the JSON (i.e. we couldn't associate a chunk
        #   to an asset above if we parse the chunk before the asset)

        # associate chunks to assets
        inserts = []
        for chunk_id, asset_names in chunk_asset_names_index.items():
            assets = db_session.query(Asset).filter(Asset.name.in_(asset_names))
            inserts.extend(
                [dict(asset_id=asset.id, chunk_id=chunk_id) for asset in assets]
            )
        db_session.execute(assets_chunks.insert(), inserts)

        # associate modules to chunks
        # FIXME: this isn't quite right - need to sort out how non-JS assets reference chunks
        inserts = []
        for module_id, chunk_external_ids in module_chunk_external_ids_index.items():
            chunks = db_session.query(Chunk).filter(
                Chunk.external_id.in_(chunk_external_ids)
            )
            inserts.extend(
                [dict(chunk_id=chunk.id, module_id=module_id) for chunk in chunks]
            )
        db_session.execute(chunks_modules.insert(), inserts)
