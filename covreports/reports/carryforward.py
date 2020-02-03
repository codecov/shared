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
    """
        Generates a carryforwarded report starting from report `report` and flags `flags`.

    What this function does it basically take a report `report` and creates a new report
        from it (so no changes are done in-place). On this new report, it adds all the information
        from the report `report` that relates to sessions that have any of the flags `f`.

    This way, for example, if none of the sessions in `report` have a flag in `flags`,
        it will just produce an empty report

    If there are sessions with any of the flags in `flags`, let's call them `relevant_sessions`,
        this function will go through all files in `report` and build a new 'carryforwarded'
        ReportFile from it, with only the ReportLines that had at least one LineSession
        among the `relevant_sessions` (and proper filter out all the the other sessions from
        that line). Then all the new EditableReportFile will be added to the report.

    Also, the old sessions are copied over to the new report, with their numbering changed to match
        the new session order they are in now (they could be the fifth session before,
        and the first session now)

    Args:
        report (Report): Description
        flags (Sequence[str]): Description

    Returns:
        EditableReport: A new report with only the info related to `flags` on it, as described above
    """
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
