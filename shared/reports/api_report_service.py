import logging

import sentry_sdk
from django.utils.functional import cached_property

from shared.api_archive.archive import ArchiveService
from shared.django_apps.core.models import Commit
from shared.helpers.flag import Flag
from shared.reports.readonly import ReadOnlyReport as SharedReadOnlyReport
from shared.reports.resources import Report
from shared.storage.exceptions import FileNotInStorageError

log = logging.getLogger(__name__)


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

    files = commit.report["files"]
    sessions = commit.report["sessions"]
    totals = commit.totals

    try:
        chunks = ArchiveService(commit.repository).read_chunks(commit.commitid)
        return build_report(chunks, files, sessions, totals, report_class=report_class)
    except FileNotInStorageError:
        log.warning(
            "File for chunks not found in storage",
            extra=dict(
                commit=commit.commitid,
                repo=commit.repository_id,
            ),
        )
        return None
