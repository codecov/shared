import logging
import random
import os

from shared.reports.resources import Report
from shared.helpers.flag import Flag
from shared.utils.match import match
from shared.metrics import metrics
from ribs import parse_report, SimpleAnalyzer, FilterAnalyzer

log = logging.getLogger(__name__)


class ReadOnlyReport(object):
    @classmethod
    def should_load_rust_version(cls):
        return random.random() < float(os.getenv("RUST_ENABLE_RATE", "0.0"))

    def __init__(self, rust_analyzer, rust_report, inner_report, totals=None):
        self.rust_analyzer = rust_analyzer
        self.rust_report = rust_report
        self.inner_report = inner_report
        self._totals = totals
        self._flags = None

    @classmethod
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
            try:
                with metrics.timer("shared.reports.readonly.from_chunks.rust") as timer:
                    rust_report = parse_report(
                        filename_mapping, chunks, session_mapping
                    )
                RUST_TIMER_THRESHOLD = 2000
                if timer.ms > RUST_TIMER_THRESHOLD:
                    log.info(
                        "Parsing in rust took longer than %d ms",
                        RUST_TIMER_THRESHOLD,
                        extra=dict(timing_ms=timer.ms),
                    )
            except Exception:
                log.warning("Could not parse report", exc_info=True)
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

    @metrics.timer("shared.reports.readonly.apply_diff")
    def apply_diff(self, *args, **kwargs):
        return self.inner_report.apply_diff(*args, **kwargs)

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
        self.rust_report = parse_report(
            filename_mapping, self.inner_report.to_archive(), session_mapping
        )
        self._totals = None
        return res

    @metrics.timer("shared.reports.readonly.calculate_diff")
    def calculate_diff(self, *args, **kwargs):
        return self.inner_report.calculate_diff(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.inner_report.get(*args, **kwargs)

    def _log_rust_differences(self, metric_python_ms, metric_rust_ms):
        if metric_python_ms > 20 * metric_rust_ms:
            metrics.incr("shared.reports.readonly._process_totals.twentyfold")
        elif metric_python_ms > 5 * metric_rust_ms:
            metrics.incr("shared.reports.readonly._process_totals.fivefold")
        elif metric_python_ms > 2 * metric_rust_ms:
            metrics.incr("shared.reports.readonly._process_totals.twofold")
        elif metric_python_ms > metric_rust_ms:
            metrics.incr("shared.reports.readonly._process_totals.better")
        else:
            metrics.incr("shared.reports.readonly._process_totals.worse")
            log.info(
                "Rust was worse than python on the metrics calculation",
                extra=dict(rust_timer=metric_rust_ms, python_timer=metric_python_ms,),
            )
        RUST_TIMER_THRESHOLD = 1000
        if metric_rust_ms > RUST_TIMER_THRESHOLD:
            log.info(
                "Processing totals in rust took longer than %d ms",
                RUST_TIMER_THRESHOLD,
            )

    @metrics.timer("shared.reports.readonly._process_totals")
    def _process_totals(self):
        metric_name = "cached" if self.inner_report._totals else "python"
        with metrics.timer(
            f"shared.reports.readonly._process_totals.{metric_name}"
        ) as metric_python:
            res = self.inner_report.totals
        try:
            if self.rust_report:
                with metrics.timer(
                    "shared.reports.readonly._process_totals.rust"
                ) as timer:
                    rust_totals = self.rust_analyzer.get_totals(self.rust_report)
                if metric_name == "python":
                    self._log_rust_differences(metric_python.ms, timer.ms)
                if (
                    rust_totals.lines != res.lines
                    or rust_totals.hits != res.hits
                    or (
                        rust_totals.coverage != res.coverage
                        and not (rust_totals.coverage is None and res.coverage == 0)
                    )
                ):
                    log.warning(
                        "Got unexpected result from rust on totals calculation",
                        extra=dict(
                            totals=res.asdict(), rust_totals=rust_totals.asdict(),
                        ),
                    )
                elif rust_totals.files != res.files:
                    log.warning(
                        "Got unexpected number of files from rust on totals calculation",
                        extra=dict(
                            totals=res.asdict(), rust_totals=rust_totals.asdict(),
                        ),
                    )
        except Exception:
            log.warning("Error while calculating rust totals", exc_info=True)
        return res

    @property
    def totals(self):
        if self._totals is None:
            self._totals = self._process_totals()
        return self._totals

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


def rustify_diff(diff):
    if diff is None or "files" not in diff:
        return None
    new_values = [
        (
            key,
            (
                value["type"],
                value.get("before"),
                [
                    (
                        tuple(int(x) if x else 0 for x in s["header"]),
                        [l[0] if l else " " for l in s["lines"]],
                    )
                    for s in value.get("segments", [])
                ],
            ),
        )
        for (key, value) in diff["files"].items()
    ]
    return dict(new_values)
