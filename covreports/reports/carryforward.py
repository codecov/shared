from typing import Sequence
import dataclasses
from time import time

from covreports.reports.resources import Report, ReportLine
from covreports.reports.editable import EditableReportFile, EditableReport
from covreports.utils.merge import (
    get_complexity_from_sessions,
    get_coverage_from_sessions,
)
from covreports.utils.match import match_any
from covreports.utils.sessions import Session, SessionType


def generate_carryforward_report(
    report: Report, flags: Sequence[str]
) -> EditableReport:
    new_report = EditableReport()
    relevant_sessions_items = {
        int(sid): session
        for sid, session in report.sessions.items()
        if match_any(flags, session.flags)
    }
    old_to_new_session_mapping = {}
    for old_sess_id, sess in relevant_sessions_items.items():
        new_session = Session(
            provider=sess.provider,
            build=sess.build,
            job=sess.job,
            name=f"CF {sess.name}" if sess.name else f"Carryforwarded",
            time=int(time()),
            id=new_report.next_session_number(),
            flags=sess.flags,
            archive=sess.archive,
            url=sess.url,
            session_type=SessionType.carryforwarded,
            totals=sess.totals
        )
        new_report.sessions[new_session.id] = new_session
        old_to_new_session_mapping[old_sess_id] = new_session.id
    for filename in report.files:
        existing_file_report = report.get(filename)
        new_file_report = EditableReportFile(existing_file_report.name)
        for line_number, report_line in existing_file_report.lines:
            new_sessions = [
                dataclasses.replace(s, id=old_to_new_session_mapping[s.id])
                for s in (report_line.sessions or [])
                if int(s.id) in relevant_sessions_items.keys()
            ]
            if new_sessions:
                new_file_report.append(
                    line_number,
                    ReportLine(
                        coverage=get_coverage_from_sessions(new_sessions),
                        complexity=get_complexity_from_sessions(new_sessions),
                        type=report_line.type,
                        sessions=new_sessions,
                        messages=report_line.messages,
                    ),
                )
        new_report.append(new_file_report)
    return new_report
