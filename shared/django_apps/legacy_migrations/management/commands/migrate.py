import logging

import redis_lock
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import connections
from django.db import transaction as django_transaction
from django.db.utils import ProgrammingError

from shared.django_apps.utils.config import RUN_ENV
from shared.helpers.redis import get_redis_connection
from shared.timeseries.helpers import is_timeseries_enabled

log = logging.getLogger(__name__)

MIGRATION_LOCK_NAME = "djang-migrations-lock"


class MockLock:
    def release(self):
        pass


"""
We need to override the base Django migrate command to handle the legacy migrations we have in the "legacy_migrations" app.
Those migrations are the source of truth for the initial db state, which is captured in Django migrations 0001 for the
core, codecov_auth and reports apps. Thus we need to fake out the initial migrations for those apps to apply duplicate migration
steps eg. creating the same table twice.  The source of truth for all other state is captured in the standard Django migrations
and can be safely applied after runnin the legacy migrations.
"""


class Command(MigrateCommand):
    def _run_initial_codecov_migrations(self, args, options):
        codecov_auth_options = {**options}
        codecov_auth_options["fake"] = True
        codecov_auth_options["app_label"] = "codecov_auth"
        codecov_auth_options["migration_name"] = "0001"

        core_options = {**options}
        core_options["fake"] = True
        core_options["app_label"] = "core"
        core_options["migration_name"] = "0001"

        reports_options = {**options}
        reports_options["fake"] = True
        reports_options["app_label"] = "reports"
        reports_options["migration_name"] = "0001"

        legacy_options = {**options}
        legacy_options["app_label"] = "legacy_migrations"
        legacy_options["migration_name"] = None

        super().handle(*args, **codecov_auth_options)
        super().handle(*args, **core_options)
        super().handle(*args, **reports_options)
        super().handle(*args, **legacy_options)

    def _run_initial_timeseries_migrations(self, args, options):
        django_auth = {**options}
        django_auth["fake"] = True
        django_auth["app_label"] = "auth"
        django_auth["migration_name"] = "0001"

        content_types = {**options}
        content_types["fake"] = True
        content_types["app_label"] = "contenttypes"
        content_types["migration_name"] = "0001"
        super().handle(*args, **django_auth)
        super().handle(*args, **content_types)

    def _fake_initial_migrations(self, cursor, args, options):
        try:
            cursor.execute("SELECT * FROM django_migrations;")
        except ProgrammingError:
            self._run_initial_codecov_migrations(args=args, options=options)

    def _fake_initial_timeseries_migrations(self, cursor, args, options):
        try:
            # If this query doesn't recognize django_migration, nor has less than 2 entries in auth/contenttypes,
            # it definitely doesn't have their initial migrations so we would run the initial timeseries migration
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = 'auth' or app = 'contenttypes';"
            )
            result = cursor.fetchone()
            if result[0] < 2:
                self._run_initial_timeseries_migrations(args=args, options=options)
        except Exception:
            self._run_initial_codecov_migrations(args=args, options=options)
            self._run_initial_timeseries_migrations(args=args, options=options)

    def _obtain_lock(self):
        """
        In certain environments we might be running mutliple servers that will try and run the migrations at the same time. This is
        not safe to do. So we have the command obtain a lock to try and run the migration. If it cannot get a lock, it will wait
        until it is able to do so before continuing to run. We need to
        wait for the lock instead of hard exiting on seeing another
        server running the migrations because we write code in such a way that the server expects for migrations to be applied before
        new code is deployed (but the opposite of new db with old code is fine).
        """
        # If we're running in a non-server environment, we don't need to worry about acquiring a lock
        if RUN_ENV == "DEV":
            return MockLock()

        redis_connection = get_redis_connection()
        lock = redis_lock.Lock(
            redis_connection, MIGRATION_LOCK_NAME, expire=180, auto_renewal=True
        )
        log.info("Trying to acquire migrations lock...")
        acquired = lock.acquire(timeout=180)

        if not acquired:
            return None

        return lock

    def handle(self, *args, **options):
        log.info("Codecov is starting migrations...")
        database = options["database"]
        try:
            db_connection = connections[database]
        except Exception:
            log.info(
                f"Failed to establish connection with {database}. Cannot do migrations"
            )
            return None
        options["run_syncdb"] = False

        lock = self._obtain_lock()

        # Failed to acquire lock due to timeout
        if not lock:
            log.error("Potential deadlock detected in api migrations.")
            raise Exception("Failed to obtain lock for api migration.")

        try:
            with db_connection.cursor() as cursor:
                self._fake_initial_migrations(cursor, args, options)

                if database == "timeseries" and is_timeseries_enabled():
                    self._fake_initial_timeseries_migrations(cursor, args, options)

            super().handle(*args, **options)
            django_transaction.commit(database)
        except:
            log.info("Codecov migrations failed.")
            raise
        else:
            log.info("Codecov migrations succeeded.")
        finally:
            lock.release()
