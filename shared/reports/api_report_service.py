import logging
import pickle
import sys

import sentry_sdk
from django.core.cache import cache
from django.utils.functional import cached_property
from prometheus_client import Gauge

from shared.api_archive.archive import ArchiveService
from shared.config import get_config
from shared.django_apps.core.models import Commit
from shared.helpers.flag import Flag
from shared.reports.readonly import ReadOnlyReport as SharedReadOnlyReport
from shared.reports.resources import Report
from shared.storage.exceptions import FileNotInStorageError

log = logging.getLogger(__name__)

report_size_gauge = Gauge(
    "codecov_report_size_bytes", "Size of the report in bytes", ["report_type"]
)


class ReportMixin:
    @cached_property
    def flags(self):
        """returns dict(:name=<Flag>)"""
        flags_dict = {}
        for session in self.sessions.values():
            if session.flags is not None:
                carriedforward = session.session_type.value == "carriedforward"
                carriedforward_from = session.session_extras.get("carriedforward_from")
                for flag in session.flags:
                    flags_dict[flag] = Flag(
                        self,
                        flag,
                        carriedforward=carriedforward,
                        carriedforward_from=carriedforward_from,
                    )
        return flags_dict


class SerializableReport(ReportMixin, Report):
    pass


class ReadOnlyReport(ReportMixin, SharedReadOnlyReport):
    pass


@sentry_sdk.trace
def build_report(chunks, files, sessions, totals, report_class=None):
    if report_class is None:
        report_class = SerializableReport
    return report_class.from_chunks(
        chunks=chunks, files=files, sessions=sessions, totals=totals
    )


@sentry_sdk.trace
def build_report_from_commit(commit: Commit, report_class=None):
    """
    Builds a `shared.reports.resources.Report` from a given commit.
    """
    if not commit.report:
        return None

    cache_enabled = get_config(
        "setup", "report_service", "cache_enabled", default=False
    )
    archive_service = ArchiveService(commit.repository)

    if cache_enabled:
        cache_key = f"reports/cache/{commit.commitid}/{report_class.__name__ if report_class else 'SerializableReport'}"

        redis_key = f"report:{commit.repository_id}:{commit.commitid}"
        cached_report = cache.get(redis_key)
        if cached_report:
            # if ttl is not expired pull from archive
            try:
                cached_data = archive_service.read_file(cache_key)
                if cached_data:
                    report = pickle.loads(cached_data)
                    return report
            except FileNotInStorageError:
                pass

    files = commit.report["files"]
    sessions = commit.report["sessions"]
    totals = commit.totals

    try:
        chunks = archive_service.read_chunks(commit.commitid)
        report = build_report(
            chunks, files, sessions, totals, report_class=report_class
        )
        # Record size metrics
        report_size = sys.getsizeof(report)
        report_size_gauge.labels(report_type=report.__class__.__name__).set(report_size)
        if report and cache_enabled:
            serialized_report = pickle.dumps(report)

            try:
                archive_service.write_file(cache_key, serialized_report)
                # Set TTL for cache in redis
                cache.set(
                    redis_key,
                    "cached",
                    timeout=get_config(
                        "setup", "report_service", "cache_timeout", default=3600
                    ),
                )
            except Exception as e:
                log.warning(
                    "Failed to cache report in archive",
                    extra=dict(
                        commit=commit.commitid, repo=commit.repository_id, error=str(e)
                    ),
                )

        return report
    except FileNotInStorageError:
        log.warning(
            "File for chunks not found in storage",
            extra=dict(
                commit=commit.commitid,
                repo=commit.repository_id,
            ),
        )
        return None
