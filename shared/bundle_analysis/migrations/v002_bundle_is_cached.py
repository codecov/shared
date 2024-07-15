from sqlalchemy import text
from sqlalchemy.orm import Session


def add_is_cached(db_session: Session):
    """
    Inserts is_cached column to bundles table
    then sets value default value to False because if there was
    no column for this it means it was created before caching
    mechanism existed
    """

    # Create new column
    stmt = """
    ALTER TABLE "bundles" ADD COLUMN "is_cached" boolean NOT NULL DEFAULT 0
    """
    db_session.execute(text(stmt))
