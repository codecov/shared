from sqlalchemy import text
from sqlalchemy.orm import Session


def add_gzip_size(db_session: Session):
    # Inserts gzip_size column to assets table
    # then sets value to 1/1000 of the uncompressed asset size
    # using this arbitrary number because that's what we've
    # historically been computing it as in the API

    # Create new column
    stmt = """
    ALTER TABLE "assets" ADD COLUMN "gzip_size" integer NOT NULL DEFAULT 0
    """
    db_session.execute(text(stmt))

    # Set default value to assets.size / 1000
    stmt = """
    UPDATE "assets" SET "gzip_size"="size"/1000
    """
    db_session.execute(text(stmt))
