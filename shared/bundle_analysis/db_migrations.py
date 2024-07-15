from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.bundle_analysis.migrations.v001_add_gzip_size import add_gzip_size
from shared.bundle_analysis.migrations.v002_bundle_is_cached import add_is_cached


class BundleAnalysisMigration:
    """
    Keeps track of DB schema migrations for the Bundle Analysis Report SQLite file
    When updating the tables/models in assets.py, the SCHEMA_VERSION needs to be
    incremented by 1, and an entry in self.migrations needs to correspond the new version
    and the SQL changes that needs to execute to update to the latest changes.
    When new bundle analysis reports are processed they will be on the latest version and
    no migration will be needed, however for commits with reports of older versions, when
    they are fetched the migrations will be applied to prevent errors with unexpected DB schemas.
    """

    def __init__(self, db_session: Session, from_version: int, to_version: int):
        self.db_session = db_session
        self.from_version = from_version
        self.to_version = to_version

        # Mapping of the schema_version number to the migration function that needs to run
        # {x: fcn} means to bring version x-1 to x, fcn must be ran
        self.migrations = {
            2: add_gzip_size,
            3: add_is_cached,
        }

    def update_schema_version(self, version):
        stmt = f"""
        UPDATE "metadata" SET "value"={version} WHERE "key"='schema_version'
        """
        self.db_session.execute(text(stmt))

    def migrate(self):
        for version in range(self.from_version + 1, self.to_version + 1):
            self.migrations[version](self.db_session)
            self.update_schema_version(version)
            self.db_session.commit()
