import dataclasses
import logging

import sentry_sdk

from shared.reports.resources import Report, ReportFile

log = logging.getLogger(__name__)

EditableReportFile = ReportFile  # re-export


class EditableReport(Report):
    file_class = EditableReportFile

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_chunks_into_reports()

    def merge(self, new_report, joined=True):
        super().merge(new_report, joined)
        for file in self:
            if isinstance(file, ReportFile):
                self._chunks[self._files.get(file.name).file_index] = file

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
                report_file = ReportFile(
                    name=filename,
                    totals=file_summary.file_totals,
                    lines=chunk,
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

        report_file: EditableReportFile
        for report_file in self._chunks:
            if report_file is None:
                continue

            all_sessions = set()

            for idx, _line in enumerate(report_file._lines):
                if not _line:
                    continue

                # this turns the line into an actual `ReportLine`
                line = report_file._lines[idx] = report_file._line(_line)

                for session in line.sessions:
                    if session.id == old_id:
                        session.id = new_id
                    all_sessions.add(session.id)

                if line.datapoints:
                    for point in line.datapoints:
                        if point.sessionid == old_id:
                            point.sessionid = new_id

            report_file._invalidate_caches()
            report_file.__present_sessions = all_sessions
