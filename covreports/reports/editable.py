import dataclasses
import logging

from covreports.reports.resources import Report, ReportFile, ReportLine
from covreports.reports.types import EMPTY
from covreports.utils.merge import merge_all
from covreports.utils.sessions import Session, SessionType

log = logging.getLogger(__name__)


class EditableReportFile(ReportFile):
    @classmethod
    def line_without_session(cls, line: ReportLine, sessionid: int):
        new_sessions = [s for s in line.sessions if s.id != sessionid]
        remaining_coverages = [s.coverage for s in new_sessions]
        if len(new_sessions) == 0:
            return EMPTY
        new_coverage = merge_all(remaining_coverages)
        return dataclasses.replace(line, sessions=new_sessions, coverage=new_coverage)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_lines_into_report_lines()

    def turn_lines_into_report_lines(self):
        self._lines = [self._line(l) if l else EMPTY for l in self._lines]

    def delete_session(self, sessionid: int):
        self._totals = None
        for index, line in enumerate(self._lines):
            if line:
                if any(s.id == sessionid for s in line.sessions):
                    self._lines[index] = self.line_without_session(line, sessionid)


class EditableReport(Report):
    file_class = EditableReportFile

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_chunks_into_reports()

    def turn_chunks_into_reports(self):
        for filename, file_summary in self._files.items():
            index = file_summary.file_index
            chunk = self._chunks[index]
            if isinstance(chunk, str):
                report_file = self.file_class(
                    name=filename,
                    totals=file_summary.file_totals,
                    lines=chunk,
                    line_modifier=None,
                )
                self._chunks[index] = report_file

    def delete_session(self, sessionid: int):
        self.reset()
        session_to_delete = self.sessions.pop(sessionid)
        sessionid = int(sessionid)
        for file in self._chunks:
            if file is not None:
                file.delete_session(sessionid)
                if file:
                    self._files[file.name] = dataclasses.replace(
                        self._files.get(file.name), file_totals=file.totals
                    )
                else:
                    del self[file.name]
        return session_to_delete

    def add_session(self, session: Session):
        sessions_to_delete = []
        for sess_id, curr_sess in self.sessions.items():
            if curr_sess.session_type == SessionType.carriedforward:
                if curr_sess.flags and session.flags:
                    if any(f in session.flags for f in curr_sess.flags):
                        sessions_to_delete.append(sess_id)
        for sess_id_to_delete in sessions_to_delete:
            log.info("Deleted session due to carriedforward overwrite")
            self.delete_session(sess_id_to_delete)
        return super().add_session(session)
