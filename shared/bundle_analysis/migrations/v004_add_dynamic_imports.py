from sqlalchemy import text
from sqlalchemy.orm import Session


def add_dynamic_imports(db_session: Session):
    """
    Adds a table called dynamic_imports (DynamicImport model name)
    This table represents for a given Chunk what are its dynamically
    imported Assets, if applicable.

    There is no data available to migrate, any older versions of bundle
    reports will be considered to not have dynamic imports
    """
    stmts = [
        """
        CREATE TABLE dynamic_imports (
            chunk_id integer not null,
            asset_id integer not null,
            primary key (chunk_id, asset_id),
            foreign key (chunk_id) references chunks (id),
            foreign key (asset_id) references assets (id)
        );
        """,
    ]

    for stmt in stmts:
        db_session.execute(text(stmt))
