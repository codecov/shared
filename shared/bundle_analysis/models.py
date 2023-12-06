from enum import Enum
from typing import List

from sqlalchemy import Column, ForeignKey, Table, create_engine, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import backref, relationship, sessionmaker

SCHEMA = """
create table sessions (
    id integer primary key,
    info text not null
);

create table metadata (
    key text primary key,
    value text not null
);

create table assets (
    id integer primary key,
    session_id integer not null,
    name text not null,
    normalized_name text not null,
    size integer not null,
    foreign key (session_id) references sessions (id)
);

create index assets_session_id on assets (session_id);
create index assets_name_index on assets (name);

create table chunks (
    id integer primary key,
    external_id text not null,
    unique_external_id text not null,
    entry boolean not null,
    initial boolean not null,
    unique (unique_external_id)
);

create table assets_chunks (
    asset_id integer not null,
    chunk_id integer not null,
    primary key (asset_id, chunk_id),
    foreign key (asset_id) references assets (id),
    foreign key (chunk_id) references chunks (id)
);

create table modules (
    id integer primary key,
    name text not null,
    size integer not null
);

create table chunks_modules (
    chunk_id integer not null,
    module_id integer not null,
    primary key (chunk_id, module_id),
    foreign key (chunk_id) references chunks (id),
    foreign key (module_id) references modules (id)
);
"""

SCHEMA_VERSION = 1

Base = declarative_base()


def get_db_session(path: str) -> DbSession:
    engine = create_engine(f"sqlite:///{path}")
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session


# table definitions for many-to-many joins
# (we're not creating models for these tables since they can be manipulated through each side of the join)

assets_chunks = Table(
    "assets_chunks",
    Base.metadata,
    Column("asset_id", ForeignKey("assets.id")),
    Column("chunk_id", ForeignKey("chunks.id")),
)

chunks_modules = Table(
    "chunks_modules",
    Base.metadata,
    Column("chunk_id", ForeignKey("chunks.id")),
    Column("module_id", ForeignKey("modules.id")),
)

# model definitions


class Session(Base):
    """
    A session represents a single bundle stats file that we ingest.
    Multiple sessions are combined into a single database to form a full
    bundle report.
    """

    __tablename__ = "sessions"

    id = Column(types.Integer, primary_key=True)
    info = Column(types.JSON)


class Metadata(Base):
    """
    Metadata about the bundle report.
    """

    __tablename__ = "metadata"

    key = Column(types.Text, primary_key=True)
    value = Column(types.JSON)


class Asset(Base):
    """
    These are the top-level artifacts that the bundling process produces.
    """

    __tablename__ = "assets"

    id = Column(types.Integer, primary_key=True)
    session_id = Column(types.Integer, ForeignKey("sessions.id"), nullable=False)
    name = Column(types.Text, nullable=False)
    normalized_name = Column(types.Text, nullable=False)
    size = Column(types.Integer, nullable=False)

    session = relationship("Session", backref=backref("assets"))
    chunks = relationship("Chunk", secondary=assets_chunks, back_populates="assets")


class Chunk(Base):
    """
    These are an intermediate form that I don't totally understand yet.
    """

    __tablename__ = "chunks"

    id = Column(types.Integer, primary_key=True)
    external_id = Column(types.Text, nullable=False)
    unique_external_id = Column(types.Text, nullable=False)
    entry = Column(types.Boolean, nullable=False)
    initial = Column(types.Boolean, nullable=False)

    assets = relationship("Asset", secondary=assets_chunks, back_populates="chunks")
    modules = relationship("Module", secondary=chunks_modules, back_populates="chunks")


class Module(Base):
    """
    These are the constituent modules that comprise an asset.
    """

    __tablename__ = "modules"

    id = Column(types.Integer, primary_key=True)
    name = Column(types.Text, nullable=False)
    size = Column(types.Integer, nullable=False)

    chunks = relationship("Chunk", secondary=chunks_modules, back_populates="modules")


class MetadataKey(Enum):
    SCHEMA_VERSION = "schema_version"
