import logging
import os
import random

from shared.helpers.flag import Flag
from shared.metrics import metrics, sentry
from shared.reports.resources import Report, ReportTotals
from shared.ribs import FilterAnalyzer, SimpleAnalyzer, parse_report
from shared.utils.match import match

log = logging.getLogger(__name__)


class LazyRustReport(object):
    def __init__(self, filename_mapping, chunks, session_mapping):
        self._chunks = chunks
        self._filename_mapping = filename_mapping
        self._session_mapping = session_mapping
        self._actual_report = None

    @sentry.trace
    def get_report(self):
        if self._actual_report is None:
            with sentry.start_span(description="Parse Rust report"):
                self._actual_report = parse_report(
                    self._filename_mapping, self._chunks, self._session_mapping
                )
                self._chunks = None  # Free the memory
        return self._actual_report


class ReadOnlyReport(object):
    @classmethod
    def should_load_rust_version(cls):
        return random.random() < float(os.getenv("RUST_ENABLE_RATE", "1.0"))

    def __init__(self, rust_analyzer, rust_report, inner_report, totals=None):
        self.rust_analyzer = rust_analyzer
        self.rust_report = rust_report
        self.inner_report = inner_report
        self._totals = totals
        self._flags = None
        self._uploaded_flags = None

    @classmethod
    @sentry.trace
    @metrics.timer("shared.reports.readonly.from_chunks")
    def from_chunks(cls, files=None, sessions=None, totals=None, chunks=None):
        rust_analyzer = SimpleAnalyzer()
        inner_report = Report(
            files=files, sessions=sessions, totals=totals, chunks=chunks
        )
        totals = inner_report._totals
        filename_mapping = {
            filename: file_summary.file_index
            for (filename, file_summary) in inner_report._files.items()
        }
        session_mapping = {
            sid: (session.flags or []) for sid, session in inner_report.sessions.items()
        }
        rust_report = None
        if cls.should_load_rust_version():
            rust_report = LazyRustReport(filename_mapping, chunks, session_mapping)
        return cls(rust_analyzer, rust_report, inner_report, totals=totals)

    @classmethod
    def create_from_report(cls, report):
        return cls.from_chunks(
            chunks=report.to_archive(),
            sessions=report.sessions,
            files=report._files,
            totals=None,
        )

    def __iter__(self):
        return iter(self.inner_report)

    @property
    def files(self):
        return self.inner_report.files

    @property
    def flags(self):
        if self._flags is None:
            self._flags = {}
            for flag_name, flag in self.inner_report.flags.items():
                self._flags[flag_name] = Flag(
                    self,
                    flag_name,
                    carriedforward=flag.carriedforward,
                    carriedforward_from=flag.carriedforward_from,
                )
        return self._flags

    @property
    def sessions(self):
        return self.inner_report.sessions

    @property
    def size(self):
        return self.inner_report.size

    @sentry.trace
    @metrics.timer("shared.reports.readonly.apply_diff")
    def apply_diff(self, *args, **kwargs):
        return self.inner_report.apply_diff(*args, **kwargs)

    @sentry.trace
    def append(self, *args, **kwargs):
        log.warning("Modifying report that is read only")
        res = self.inner_report.append(*args, **kwargs)
        filename_mapping = {
            filename: file_summary.file_index
            for (filename, file_summary) in self.inner_report._files.items()
        }
        session_mapping = {
            sid: (session.flags or [])
            for sid, session in self.inner_report.sessions.items()
        }
        self.rust_report = LazyRustReport(
            filename_mapping, self.inner_report.to_archive(), session_mapping
        )
        self._totals = None
        return res

    @sentry.trace
    @metrics.timer("shared.reports.readonly.calculate_diff")
    def calculate_diff(self, *args, **kwargs):
        return self.inner_report.calculate_diff(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.inner_report.get(*args, **kwargs)

    @sentry.trace
    @metrics.timer("shared.reports.readonly._process_totals")
    def _process_totals(self):
        if self.inner_report.has_precalculated_totals():
            return self.inner_report.totals
        if self.rust_report:
            res = self.rust_analyzer.get_totals(self.rust_report.get_report())
            return ReportTotals(
                files=res.files,
                lines=res.lines,
                hits=res.hits,
                misses=res.misses,
                partials=res.partials,
                coverage=res.coverage,
                branches=res.branches,
                methods=res.methods,
                messages=0,
                sessions=res.sessions,
                complexity=res.complexity,
                complexity_total=res.complexity_total,
                diff=0,
            )
        return self.inner_report.totals

    @property
    def totals(self):
        if self._totals is None:
            self._totals = self._process_totals()
        return self._totals

    def get_file_totals(self, path):
        return self.inner_report.get_file_totals(path)

    @sentry.trace
    def filter(self, paths=None, flags=None):
        if paths is None and flags is None:
            return self
        matching_files = (
            set(f for f in self.files if match(paths, f)) if paths else None
        )
        rust_analyzer = FilterAnalyzer(
            files=matching_files, flags=flags if flags else None
        )
        return ReadOnlyReport(
            rust_analyzer,
            rust_report=self.rust_report,
            inner_report=self.inner_report.filter(paths=paths, flags=flags),
        )

    def get_uploaded_flags(self):
        if self._uploaded_flags is None:
            self._uploaded_flags = self.inner_report.get_uploaded_flags()
        return self._uploaded_flags
