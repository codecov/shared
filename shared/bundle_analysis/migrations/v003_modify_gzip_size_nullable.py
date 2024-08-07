from sqlalchemy import text
from sqlalchemy.orm import Session


def modify_gzip_size_nullable(db_session: Session):
    """
    Modify gzip_size column of assets table to be a nullable value
    Because SQLite does not have a "alter column" command we need to
    rename the existing table, create the new table, and migrate all the data over
    """

    # Update column
    stmt = """
    PRAGMA foreign_keys=off;

    BEGIN TRANSACTION;

    ALTER TABLE assets RENAME TO assets_old;

    create table assets (
        id integer primary key,
        session_id integer not null,
        name text not null,
        normalized_name text not null,
        size integer not null,
        gzip_size integer,
        uuid text not null,
        asset_type text not null,
        foreign key (session_id) references sessions (id)
    );

    INSERT INTO assets (id, session_id, name, normalized_name, size, gzip_size, uuid, asset_type)
    SELECT id, session_id, name, normalized_name, size, gzip_size, uuid, asset_type
    FROM assets_old;

    DROP TABLE assets_old;

    COMMIT;

    PRAGMA foreign_keys=on;
    """
    db_session.execute(text(stmt))
