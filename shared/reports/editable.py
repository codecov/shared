import dataclasses
import logging
from copy import copy
from typing import List

from shared.reports.resources import Report, ReportFile
from shared.reports.types import EMPTY

log = logging.getLogger(__name__)


class EditableReportFile(ReportFile):
    __slots__ = ("_details",)

    @classmethod
    def from_ReportFile(cls, report_file: ReportFile):
        name = report_file.name
        editable_file = cls(name)
        editable_file._totals = report_file._totals
        editable_file._lines = report_file._lines
        editable_file._line_modifier = report_file._line_modifier
        editable_file._ignore = report_file._ignore
        editable_file._details = report_file._details
        editable_file.fix_details()
        return editable_file

    def fix_details(self):
        if self._details is None:
            self._details = {}
        if self._details.get("present_sessions") is not None:
            self._details["present_sessions"] = set(
                self._details.get("present_sessions")
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fix_details()

    @property
    def details(self):
        if not self._details:
            return self._details
        if self._details.get("present_sessions") is None:
            return self._details
        res = copy(self._details)
        res["present_sessions"] = sorted(self._details.get("present_sessions"))
        return res

    def delete_labels(
        self, session_ids_to_delete: List[int], label_ids_to_delete: List[int]
    ):
        """Given a list of session_ids and label_ids to delete
        Remove all datapoints that belong to at least 1 session_ids to delete and include
        at least 1 of the label_ids to be removed
        """
        for index, line in self.lines:
            if line.datapoints is not None:
                if any(
                    (
                        dp.sessionid in session_ids_to_delete
                        and label_id in label_ids_to_delete
                    )
                    for dp in line.datapoints
                    for label_id in dp.label_ids
                ):
                    # Line fits change requirements
                    new_line = self.line_without_labels(
                        line, session_ids_to_delete, label_ids_to_delete
                    )
                    if new_line == EMPTY:
                        del self[index]
                    else:
                        self[index] = new_line
        self._totals = None
        self.calculate_present_sessions()

    def calculate_present_sessions(self):
        all_sessions = set()
        for _, line in self.lines:
            all_sessions.update(int(s.id) for s in line.sessions)
        self._details["present_sessions"] = all_sessions

    def merge(self, *args, **kwargs):
        res = super().merge(*args, **kwargs)
        self.calculate_present_sessions()
        return res

    def delete_multiple_sessions(self, session_ids_to_delete: set[int]):
        if "present_sessions" not in self._details:
            self.calculate_present_sessions()
        current_sessions = self._details["present_sessions"]

        new_sessions = current_sessions.difference(session_ids_to_delete)
        if current_sessions == new_sessions:
            return  # nothing to do

        self._details["present_sessions"] = new_sessions
        self._totals = None  # force a refresh of the on-demand totals

        if not new_sessions:
            self._lines = []  # no remaining sessions means no line data
            return

        for index, line in self.lines:
            if any(s.id in session_ids_to_delete for s in line.sessions):
                new_line = self.line_without_multiple_sessions(
                    line, session_ids_to_delete
                )
                if new_line == EMPTY:
                    del self[index]
                else:
                    self[index] = new_line


class EditableReport(Report):
    file_class = EditableReportFile

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_chunks_into_reports()

    def merge(self, new_report, joined=True):
        super().merge(new_report, joined)
        for file in self:
            if isinstance(file, ReportFile):
                self._chunks[self._files.get(file.name).file_index] = (
                    EditableReportFile.from_ReportFile(file)
                )

    def turn_chunks_into_reports(self):
        filename_mapping = {
            file_summary.file_index: filename
            for filename, file_summary in self._files.items()
        }
        for chunk_index in range(len(self._chunks)):
            filename = filename_mapping.get(chunk_index)
            file_summary = self._files.get(filename)
            chunk = self._chunks[chunk_index]
            if chunk is not None and file_summary is not None:
                if isinstance(chunk, ReportFile):
                    chunk = chunk._lines
                report_file = self.file_class(
                    name=filename,
                    totals=file_summary.file_totals,
                    lines=chunk,
                    line_modifier=None,
                )
                self._chunks[chunk_index] = report_file
            else:
                self._chunks[chunk_index] = None

    def delete_labels(self, sessionids, labels_to_delete):
        self._totals = None
        for file in self._chunks:
            if file is not None:
                file.delete_labels(sessionids, labels_to_delete)
                if file:
                    self._files[file.name] = dataclasses.replace(
                        self._files[file.name],
                        file_totals=file.totals,
                    )
                else:
                    del self[file.name]
        return sessionids

    def delete_multiple_sessions(self, session_ids_to_delete: list[int] | set[int]):
        session_ids_to_delete = set(session_ids_to_delete)
        self._totals = None
        for sessionid in session_ids_to_delete:
            self.sessions.pop(sessionid)

        for file in self._chunks:
            if file is not None:
                file.delete_multiple_sessions(session_ids_to_delete)
                if file:
                    self._files[file.name] = dataclasses.replace(
                        self._files[file.name],
                        file_totals=file.totals,
                    )
                else:
                    del self[file.name]
