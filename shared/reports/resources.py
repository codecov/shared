import dataclasses
import logging
from copy import copy
from itertools import filterfalse
from typing import Any, Generator

import orjson
import sentry_sdk

from shared.helpers.flag import Flag
from shared.helpers.yaml import walk
from shared.reports.diff import CalculatedDiff, RawDiff, calculate_report_diff
from shared.reports.exceptions import LabelIndexNotFoundError, LabelNotFoundError
from shared.reports.filtered import FilteredReport
from shared.reports.reportfile import ReportFile
from shared.reports.serde import orjson_option, report_default
from shared.reports.types import (
    TOTALS_MAP,
    ReportFileSummary,
    ReportHeader,
    ReportTotals,
)
from shared.utils.flare import report_to_flare
from shared.utils.make_network_file import make_network_file
from shared.utils.migrate import migrate_totals
from shared.utils.sessions import Session, SessionType
from shared.utils.totals import agg_totals

log = logging.getLogger(__name__)


def unique_everseen(iterable):
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add
    for element in filterfalse(seen.__contains__, iterable):
        seen_add(element)
        yield element


END_OF_CHUNK = "\n<<<<< end_of_chunk >>>>>\n"
END_OF_HEADER = "\n<<<<< end_of_header >>>>>\n"


def chunks_from_storage_contains_header(chunks: str) -> bool:
    try:
        first_line_end = chunks.index("\n")
        second_line_end = chunks.index("\n", first_line_end + 1)
    except ValueError:
        return False
    # If the header is present then the END_OF_HEADER marker
    # is in the 2nd line of the report
    return chunks[first_line_end : second_line_end + 1] == END_OF_HEADER


@sentry_sdk.trace
def build_files(files: dict[str, Any]) -> dict[str, ReportFileSummary]:
    # NOTE: this mutates `files` in-place
    for filename, file_summary in files.items():
        if not isinstance(file_summary, ReportFileSummary):
            # We have a minimum of two pieces of data
            chunks_index = file_summary[0]
            file_totals = file_summary[1]

            try:
                # Indices 2 and 3 may not exist. Index 2 used to be `session_totals`
                # but is ignored now due to a bug.
                diff_totals = file_summary[3]
            except IndexError:
                diff_totals = None

            files[filename] = ReportFileSummary(chunks_index, file_totals, diff_totals)
    return files


def get_sessions(sessions: dict) -> dict[int, Session]:
    return {
        int(sid): copy(session)
        if isinstance(session, Session)
        else Session.parse_session(**session)
        for sid, session in sessions.items()
    }


def parse_header(header: str) -> ReportHeader:
    if header == "":
        return ReportHeader()
    header = orjson.loads(header)
    return ReportHeader(
        # JSON can only have str as keys. We cast to int.
        # Because encoded labels in the CoverageDatapoint level are ints.
        labels_index={int(k): v for k, v in header.get("labels_index", {}).items()}
    )


@sentry_sdk.trace
def parse_chunks(chunks: str) -> tuple[list[str], ReportHeader]:
    # came from archive
    # split the details header, which is JSON
    if chunks_from_storage_contains_header(chunks):
        header_str, chunks = chunks.split(END_OF_HEADER, 1)
        header = parse_header(header_str)
    else:
        header = ReportHeader()
    split_chunks = chunks.split(END_OF_CHUNK)

    return (split_chunks, header)


class Report(object):
    _files: dict[str, ReportFileSummary]
    _header: ReportHeader

    def __init__(
        self,
        files=None,
        sessions=None,
        totals=None,
        chunks=None,
        diff_totals=None,
        **kwargs,
    ):
        # {"filename": [<line index in chunks :int>, <ReportTotals>]}
        self._files = build_files(files) if files else {}
        # {1: {...}}
        self.sessions = get_sessions(sessions) if sessions else {}

        # ["<json>", ...]
        self._chunks: list[str | ReportFile]
        self._chunks, self._header = (
            parse_chunks(chunks)
            if chunks and isinstance(chunks, str)
            else (chunks or [], ReportHeader())
        )

        # <ReportTotals>
        self._totals: ReportTotals | None = None
        if isinstance(totals, ReportTotals):
            self._totals = totals
        elif totals:
            self._totals = ReportTotals(*migrate_totals(totals))

        self.diff_totals = diff_totals

    def _invalidate_caches(self):
        self._totals = None

    @property
    def totals(self):
        if not self._totals:
            self._totals = self._process_totals()
        return self._totals

    def _process_totals(self):
        """Runs through the file network to aggregate totals
        returns <ReportTotals>
        """

        def _iter_totals():
            for filename, data in self._files.items():
                if data.file_totals is None:
                    yield self.get(filename).totals
                else:
                    yield data.file_totals

        totals = agg_totals(_iter_totals())
        totals.sessions = len(self.sessions)
        return totals

    def _iter_parsed_files(self) -> Generator[ReportFile, None, None]:
        for name, summary in self._files.items():
            idx = summary.file_index
            file = self._chunks[idx]
            if not isinstance(file, ReportFile):
                file = self._chunks[idx] = ReportFile(
                    name=name, totals=summary.file_totals, lines=file
                )
            yield file

    @property
    def header(self) -> ReportHeader:
        return self._header

    @header.setter
    def header(self, value: ReportHeader):
        self._header = value

    @property
    def labels_index(self) -> dict[int, str] | None:
        return self._header.get("labels_index")

    @labels_index.setter
    def labels_index(self, value: dict[int, str]):
        self.header = {**self.header, "labels_index": value}

    def lookup_label_by_id(self, label_id: int) -> str:
        if self.labels_index is None:
            raise LabelIndexNotFoundError()
        if label_id not in self.labels_index:
            raise LabelNotFoundError()
        return self.labels_index[label_id]

    @classmethod
    def from_chunks(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    @property
    def size(self):
        size = 0
        for chunk in self._chunks:
            size += len(chunk)
        return size

    def has_precalculated_totals(self):
        return self._totals is not None

    @property
    def network(self):
        for fname, data in self._files.items():
            yield (
                fname,
                make_network_file(data.file_totals, data.diff_totals),
            )

    def __repr__(self):
        try:
            return "<%s files=%s>" % (
                self.__class__.__name__,
                len(getattr(self, "_files", [])),
            )
        except Exception:
            return "<%s files=n/a>" % self.__class__.__name__

    @property
    def files(self) -> list[str]:
        """returns a list of files in the report"""
        return list(self._files.keys())

    @property
    def flags(self):
        """returns dict(:name=<Flag>)"""
        flags_dict = {}
        for session in self.sessions.values():
            if session.flags:
                # If the session was carriedforward, mark its flags as carriedforward
                session_carriedforward = (
                    session.session_type == SessionType.carriedforward
                )
                session_carriedforward_from = getattr(
                    session, "session_extras", {}
                ).get("carriedforward_from")

                for flag in session.flags:
                    flags_dict[flag] = Flag(
                        self,
                        flag,
                        carriedforward=session_carriedforward,
                        carriedforward_from=session_carriedforward_from,
                    )
        return flags_dict

    def get_flag_names(self) -> list[str]:
        all_flags = set()
        for session in self.sessions.values():
            if session and session.flags:
                all_flags.update(session.flags)
        return sorted(all_flags)

    def append(self, _file, joined=True):
        """adds or merged a file into the report"""
        if _file is None:
            # skip empty adds
            return False

        elif not isinstance(_file, ReportFile):
            raise TypeError("expecting ReportFile got %s" % type(_file))

        elif len(_file) == 0:
            # dont append empty files
            return False

        assert _file.name, "file must have a name"

        # check if file already exists
        index = self._files.get(_file.name)
        if index:
            # existing file
            # =============
            #  merge old report chunk
            cur_file = self[_file.name]
            # merge it
            cur_file.merge(_file, joined)
            # set totals
            index.file_totals = cur_file.totals
            # update chunk in report
            self._chunks[index.file_index] = cur_file
        else:
            # new file
            # ========
            # override totals
            if not joined:
                _file._totals = ReportTotals(0, _file.totals.lines)

            # add to network
            self._files[_file.name] = ReportFileSummary(
                len(self._chunks),  # chunk location
                _file.totals,  # Totals
                None,  # Diff Totals
            )

            # add file in chunks
            self._chunks.append(_file)

        self._totals = None

        return True

    def get(self, filename, _else=None, bind=False):
        """
        returns <ReportFile>
        if not found return _else

        :bind will replace the chunks and bind file changes to the report
        """
        _file = self._files.get(filename)
        if _file is not None:
            if self._chunks:
                try:
                    lines = self._chunks[_file.file_index]
                except IndexError:
                    log.warning(
                        "File not found in chunk",
                        extra=dict(file_index=_file.file_index),
                        exc_info=True,
                    )
                    lines = None
            else:
                # may be tree_only request
                lines = None
            if isinstance(lines, ReportFile):
                return lines
            report_file = ReportFile(
                name=filename,
                totals=_file.file_totals,
                lines=lines,
            )
            if bind:
                self._chunks[_file.file_index] = report_file

            return report_file

        return _else

    def resolve_paths(self, paths):
        """
        :paths [(old_path, new_path), ...]
        """
        already_added_to_file = []
        paths_to_use = list(unique_everseen(paths))
        if len(paths_to_use) < len(paths):
            log.info("Paths being resolved were duplicated. Deduplicating")
        for old_path, new_path in paths_to_use:
            if old_path in self:
                if new_path in already_added_to_file:
                    del self[old_path]
                elif new_path is None:
                    del self[old_path]
                else:
                    already_added_to_file.append(new_path)
                    if old_path != new_path:
                        # rename and ignore lines
                        self.rename(old_path, new_path)

    def rename(self, old, new):
        # remvoe from list
        _file = self._files.pop(old)
        # add back with new name
        self._files[new] = _file
        # update name if it was a ReportFile
        chunk = self._chunks[_file.file_index]
        if isinstance(chunk, ReportFile):
            chunk.name = new
        return True

    def __getitem__(self, filename):
        _file = self.get(filename)
        if _file is None:
            raise IndexError("File at path %s not found in report" % filename)
        return _file

    def __delitem__(self, filename):
        # remove from report
        _file = self._files.pop(filename)
        # remove chunks
        self._chunks[_file.file_index] = None
        return True

    def get_file_totals(self, path: str) -> ReportTotals | None:
        if path not in self._files:
            log.warning(
                "Fetching file totals for a file that isn't in the report",
                extra=dict(path=path),
            )
            return None

        totals = self._files[path].file_totals
        if isinstance(totals, ReportTotals):
            return totals
        else:
            return ReportTotals(*totals)

    def next_session_number(self):
        start_number = len(self.sessions)
        while start_number in self.sessions or str(start_number) in self.sessions:
            start_number += 1
        return start_number

    def add_session(self, session, use_id_from_session=False):
        sessionid = session.id if use_id_from_session else self.next_session_number()
        self.sessions[sessionid] = session
        if self._totals:
            # add session to totals
            if use_id_from_session:
                self._totals = dataclasses.replace(
                    self._totals, sessions=self._totals.sessions + 1
                )
            else:
                self._totals = dataclasses.replace(self._totals, sessions=sessionid + 1)

        return sessionid, session

    def __iter__(self):
        """Iter through all the files
        yielding <ReportFile>
        """
        for filename, _file in self._files.items():
            if self._chunks:
                report = self._chunks[_file.file_index]
            else:
                report = None
            if isinstance(report, ReportFile):
                yield report
            else:
                yield ReportFile(
                    name=filename,
                    totals=_file.file_totals,
                    lines=report,
                )

    def __contains__(self, filename):
        return filename in self._files

    @sentry_sdk.trace
    def merge(self, new_report, joined=True):
        """combine report data from another"""
        if new_report is None:
            return

        elif not isinstance(new_report, Report):
            raise TypeError("expecting type Report got %s" % type(new_report))

        elif new_report.is_empty():
            return

        # merge files
        for _file in new_report:
            if _file.name:
                self.append(_file, joined)

        self._totals = self._process_totals()

    def is_empty(self):
        """returns boolean if the report has no content"""
        return len(self._files) == 0

    def __bool__(self):
        return self.is_empty() is False

    @sentry_sdk.trace
    def to_archive(self, with_header=True):
        # TODO: confirm removing encoding here is fine
        chunks = END_OF_CHUNK.join(_encode_chunk(chunk) for chunk in self._chunks)
        if with_header:
            # When saving to database we want this
            return END_OF_HEADER.join(
                [orjson.dumps(self._header, option=orjson_option).decode(), chunks]
            )
        # This is helpful to build ReadOnlyReport
        # Because Rust can't parse the header. It doesn't need it either,
        # So it's simpler to just never sent it.
        return chunks

    @sentry_sdk.trace
    def to_database(self):
        """returns (totals, report) to be stored in database"""
        totals = dict(zip(TOTALS_MAP, self.totals))
        totals["diff"] = self.diff_totals
        return (
            totals,
            orjson.dumps(
                {"files": self._files, "sessions": self.sessions},
                default=report_default,
                option=orjson_option,
            ).decode(),
        )

    @sentry_sdk.trace
    def flare(self, changes=None, color=None):
        if changes is not None:
            """
            if changes are provided we produce a new network
            only pass totals if they change
            """
            # <dict path: totals if not new else None>
            changed_coverages = dict(
                (
                    (
                        individual_change.path,
                        individual_change.totals.coverage
                        if not individual_change.new and individual_change.totals
                        else None,
                    )
                    for individual_change in changes
                )
            )
            # <dict path: stripeed if not in_diff>
            classes = dict(
                ((_Change.path, "s") for _Change in changes if not _Change.in_diff)
            )

            def _network():
                for name, _NetworkFile in self.network:
                    changed_coverage = changed_coverages.get(name)
                    if changed_coverage:
                        # changed file
                        yield (
                            name,
                            ReportTotals(
                                lines=_NetworkFile.totals.lines,
                                coverage=float(changed_coverage),
                            ),
                        )
                    else:
                        diff = _NetworkFile.diff_totals
                        if diff and diff.lines > 0:  # lines > 0
                            # diff file
                            yield (
                                name,
                                ReportTotals(
                                    lines=_NetworkFile.totals.lines,
                                    coverage=-1
                                    if float(diff.coverage)
                                    < float(_NetworkFile.totals.coverage)
                                    else 1,
                                ),
                            )

                        else:
                            # unchanged file
                            yield name, ReportTotals(lines=_NetworkFile.totals.lines)

            network = _network()

            def color(cov):
                return (
                    "purple"
                    if cov is None
                    else "#e1e1e1"
                    if cov == 0
                    else "green"
                    if cov > 0
                    else "red"
                )

        else:
            network = (
                (path, _NetworkFile.totals) for path, _NetworkFile in self.network
            )
            classes = {}
            # [TODO] [v4.4.0] remove yaml from args, use below
            # color = self.yaml.get(('coverage', 'range'))

        return report_to_flare(network, color, classes)

    def filter(self, paths=None, flags=None):
        if paths:
            if not isinstance(paths, (list, set, tuple)):
                raise TypeError(
                    "expecting list for argument paths got %s" % type(paths)
                )
        if paths is None and flags is None:
            return self
        return FilteredReport(self, path_patterns=paths, flags=flags)

    @sentry_sdk.trace
    def does_diff_adjust_tracked_lines(self, diff, future_report, future_diff):
        """
        Returns <boolean> if the diff touches tracked lines

        master . A . C
        pull          | . . B

        :diff = <diff> A...C
        :future_report = <report> B
        :future_diff = <diff> C...B

        future_report is necessary because it is used to determin if
        lines added in the diff are tracked by codecov
        """
        if diff and diff.get("files"):
            for path, data in diff["files"].items():
                future_state = walk(future_diff, ("files", path, "type"))
                if data["type"] == "deleted" and path in self:  # deleted  # and tracked
                    # found a file that was tracked and deleted
                    return True

                elif (
                    data["type"] == "new"
                    and future_state != "deleted"  # newly tracked
                    and path  # not deleted in future
                    in future_report  # found in future
                ):
                    # newly tracked file
                    return True

                elif data["type"] == "modified":
                    in_past = path in self
                    in_future = future_state != "deleted" and path in future_report
                    if in_past and in_future:
                        # get the future version
                        future_file = future_report.get(path, bind=False)
                        # if modified
                        if future_state == "modified":
                            # shift the lines to "guess" what C was
                            future_file.shift_lines_by_diff(
                                future_diff["files"][path], forward=False
                            )

                        if self.get(path).does_diff_adjust_tracked_lines(
                            data, future_file
                        ):
                            # lines changed
                            return True

                    elif in_past and not in_future:
                        # missing in future
                        return True

                    elif not in_past and in_future:
                        # missing in pats
                        return True

        return False

    @sentry_sdk.trace
    def shift_lines_by_diff(self, diff, forward=True):
        """
        [volitile] will permanently adjust repot report

        Takes a <diff> and offsets the line based on additions and removals
        """
        if diff and diff.get("files"):
            for path, data in diff["files"].items():
                if data["type"] == "modified" and path in self:
                    _file = self.get(path)
                    _file.shift_lines_by_diff(data, forward=forward)
                    _file._totals = None
                    chunk_loc = self._files[path].file_index
                    # update chunks with file updates
                    self._chunks[chunk_loc] = _file
                    # clear out totals
                    self._files[path] = ReportFileSummary(
                        file_index=chunk_loc,
                        file_totals=_file.totals,
                        diff_totals=None,
                    )

    def calculate_diff(self, diff: RawDiff) -> CalculatedDiff:
        """
        Calculates the per-file totals (and total) of the parts
            from a `git diff` that are relevant in the report
        """
        return calculate_report_diff(self, diff)

    def save_diff_calculation(self, diff, diff_result):
        diff["totals"] = diff_result["general"]
        self.diff_totals = diff["totals"]
        for filename, file_totals in diff_result["files"].items():
            data = diff["files"].get(filename)
            data["totals"] = file_totals
            network_file = self._files[filename]
            if file_totals.lines == 0:
                file_totals = dataclasses.replace(  # noqa: PLW2901
                    file_totals, coverage=None, complexity=None, complexity_total=None
                )
            network_file.diff_totals = file_totals

    @sentry_sdk.trace
    def apply_diff(self, diff, _save=True):
        """
        Add coverage details to the diff at ['coverage'] = <ReportTotals>
        returns <ReportTotals>
        """
        if not diff or not diff.get("files"):
            return None
        totals = self.calculate_diff(diff)
        if _save and totals:
            self.save_diff_calculation(diff, totals)
        return totals.get("general")

    def get_uploaded_flags(self):
        flags = set()
        for sess in self.sessions.values():
            if sess.session_type == SessionType.uploaded and sess.flags is not None:
                flags.update(sess.flags)
        return flags

    @sentry_sdk.trace
    def repack(self):
        """Repacks in a more compact format to avoid deleted files and such"""
        if not self._passes_integrity_analysis():
            log.warning(
                "There was some integrity issus, not repacking to not accidentally damage it more"
            )
            return
        new_chunks = [x for x in self._chunks if x is not None]
        if len(new_chunks) == len(self._chunks):
            return
        notnull_chunks_new_location = list(
            enumerate(
                origin_ind
                for (origin_ind, x) in enumerate(self._chunks)
                if x is not None
            )
        )
        chunks_mapping = {b: a for (a, b) in notnull_chunks_new_location}
        for summary in self._files.values():
            summary.file_index = chunks_mapping.get(summary.file_index)
        self._chunks = new_chunks
        log.info("Repacked files in report")

    def _passes_integrity_analysis(self):
        declared_files_in_db = {f.file_index for f in self._files.values()}
        declared_files_in_chunks = {
            i for (i, j) in enumerate(self._chunks) if j is not None
        }
        if declared_files_in_db != declared_files_in_chunks:
            log.warning(
                "File has integrity issues",
                extra=dict(
                    files_only_in_db=sorted(
                        declared_files_in_db - declared_files_in_chunks
                    ),
                    files_only_in_chunks=sorted(
                        declared_files_in_chunks - declared_files_in_db
                    ),
                ),
            )
            return False
        return True

    def delete_labels(
        self, sessionids: list[int] | set[int], labels_to_delete: list[int] | set[int]
    ):
        files_to_delete = []
        for file in self._iter_parsed_files():
            file.delete_labels(sessionids, labels_to_delete)
            if file:
                self._files[file.name] = dataclasses.replace(
                    self._files[file.name],
                    file_totals=file.totals,
                )
            else:
                files_to_delete.append(file.name)
        for file in files_to_delete:
            del self[file]

        self._invalidate_caches()
        return sessionids

    def delete_multiple_sessions(self, session_ids_to_delete: list[int] | set[int]):
        session_ids_to_delete = set(session_ids_to_delete)
        for sessionid in session_ids_to_delete:
            self.sessions.pop(sessionid)

        files_to_delete = []
        for file in self._iter_parsed_files():
            file.delete_multiple_sessions(session_ids_to_delete)
            if file:
                self._files[file.name] = dataclasses.replace(
                    self._files[file.name],
                    file_totals=file.totals,
                )
            else:
                files_to_delete.append(file.name)
        for file in files_to_delete:
            del self[file]

        self._invalidate_caches()

    @sentry_sdk.trace
    def change_sessionid(self, old_id: int, new_id: int):
        """
        This changes the session with `old_id` to have `new_id` instead.
        It patches up all the references to that session across all files and line records.

        In particular, it changes the id in all the `LineSession`s and `CoverageDatapoint`s,
        and does the equivalent of `calculate_present_sessions`.
        """
        session = self.sessions[new_id] = self.sessions.pop(old_id)
        session.id = new_id

        for file in self._iter_parsed_files():
            all_sessions = set()

            for idx, _line in enumerate(file._lines):
                if not _line:
                    continue

                # this turns the line into an actual `ReportLine`
                line = file._lines[idx] = file._line(_line)

                for session in line.sessions:
                    if session.id == old_id:
                        session.id = new_id
                    all_sessions.add(session.id)

                if line.datapoints:
                    for point in line.datapoints:
                        if point.sessionid == old_id:
                            point.sessionid = new_id

            file._invalidate_caches()
            file.__present_sessions = all_sessions

        self._invalidate_caches()


def chunk_default(obj):
    if dataclasses.is_dataclass(obj):
        return obj.astuple()
    return obj


def _encode_chunk(chunk) -> str:
    if chunk is None:
        return "null"
    elif isinstance(chunk, ReportFile):
        return chunk._encode()
    elif isinstance(chunk, (list, dict)):
        return orjson.dumps(chunk, default=chunk_default, option=orjson_option).decode()
    else:
        return chunk
