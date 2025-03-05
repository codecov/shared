import logging
import os
import random
from typing import Any

import orjson
import sentry_sdk
from cc_rustyribs import FilterAnalyzer, SimpleAnalyzer, parse_report

from shared.helpers.flag import Flag
from shared.reports.resources import (
    END_OF_HEADER,
    Report,
    ReportTotals,
    chunks_from_storage_contains_header,
)
from shared.utils.match import Matcher

log = logging.getLogger(__name__)


class LazyRustReport(object):
    def __init__(self, filename_mapping, chunks, session_mapping):
        # Because Rust can't parse the header. It doesn't need it either,
        # So it's simpler to just never sent it.
        if chunks_from_storage_contains_header(chunks):
            _, chunks = chunks.split(END_OF_HEADER, 1)
        self._chunks = chunks
        self._filename_mapping = filename_mapping
        self._session_mapping = session_mapping
        self._actual_report = None

    @sentry_sdk.trace
    def _parse_report(self):
        parsed = parse_report(
            self._filename_mapping, self._chunks, self._session_mapping
        )
        self._chunks = None  # Free the memory
        return parsed

    def get_report(self):
        if self._actual_report is None:
            self._actual_report = self._parse_report()
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
    def create_from_report(cls, report: Report):
        report_json: Any
        report_json, chunks, totals = report.serialize()
        report_json = orjson.loads(report_json)

        return cls.from_chunks(
            chunks=chunks.decode(),
            sessions=report.sessions,
            files=report_json["files"],
            totals=totals,
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

    def get_flag_names(self) -> list[str]:
        return self.inner_report.get_flag_names()

    @property
    def sessions(self):
        return self.inner_report.sessions

    @property
    def size(self):
        return self.inner_report.size

    def apply_diff(self, *args, **kwargs):
        return self.inner_report.apply_diff(*args, **kwargs)

    def calculate_diff(self, *args, **kwargs):
        return self.inner_report.calculate_diff(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.inner_report.get(*args, **kwargs)

    @sentry_sdk.trace
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

    def filter(self, paths=None, flags=None):
        if paths is None and flags is None:
            return self
        matcher = Matcher(paths)
        matching_files = (
            set(f for f in self.files if matcher.match(f)) if paths else None
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
