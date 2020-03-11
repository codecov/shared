from typing import Sequence
import re
import dataclasses
from time import time

from covreports.reports.resources import Report, ReportLine
from covreports.reports.editable import EditableReportFile, EditableReport
from covreports.utils.merge import (
    get_complexity_from_sessions,
    get_coverage_from_sessions,
)
from covreports.utils.match import match_any, match
from covreports.utils.sessions import Session, SessionType


def generate_carryforward_report_file(existing_file_report, old_to_new_session_mapping):
    new_file_report = EditableReportFile(existing_file_report.name)
    for line_number, report_line in existing_file_report.lines:
        new_sessions = [
            dataclasses.replace(s, id=old_to_new_session_mapping[s.id])
            for s in (report_line.sessions or [])
            if int(s.id) in old_to_new_session_mapping.keys()
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
    return new_file_report


def carriedforward_session_name(original_session_name: str) -> str:
    if not original_session_name:
        return "Carriedforward"
    elif original_session_name.startswith("CF "):
        count = 0
        current_name = original_session_name
        while current_name.startswith("CF "):
            current_name = current_name.replace("CF ", "", 1)
            count += 1
        return f"CF[{count + 1}] - {current_name}"
    elif original_session_name.startswith("CF"):
        regex = r"CF\[(\d*)\]"
        res = re.match(regex, original_session_name)
        if res:
            number_so_far = int(res.group(1))
            return re.sub(regex, f"CF[{number_so_far + 1}]", original_session_name, count=1)
    return f"CF[1] - {original_session_name}"


def generate_carryforward_report(
    report: Report, flags: Sequence[str], paths: Sequence[str]
) -> EditableReport:
    """
        Generates a carriedforward report starting from report `report`, flags `flags`
            and paths `paths`

    What this function does it basically take a report `report` and creates a new report
        from it (so no changes are done in-place). On this new report, it adds all the information
        from `report` that relates to sessions that have any of the flags `f`

    This way, for example, if none of the sessions in `report` have a flag in `flags`,
        it will just produce an empty report

    If there are sessions with any of the flags in `flags`, let's call them `relevant_sessions`,
        this function will go through all files in `report` that match any of the paths `paths
        and build a new 'carriedforward' ReportFile from it, with only the ReportLines
        that had at least one LineSession among the `relevant_sessions` (and proper filter out
        all the the other sessions from that line). Then all the new EditableReportFile will
        be added to the report.

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
            name=carriedforward_session_name(sess.name),
            time=int(time()),
            id=new_report.next_session_number(),
            flags=sess.flags,
            archive=sess.archive,
            url=sess.url,
            session_type=SessionType.carriedforward,
            totals=sess.totals,
        )
        new_report.sessions[new_session.id] = new_session
        old_to_new_session_mapping[old_sess_id] = new_session.id
    for filename in report.files:
        if not paths or match(paths, filename):
            existing_file_report = report.get(filename)
            new_file_report = generate_carryforward_report_file(
                existing_file_report, old_to_new_session_mapping
            )
            new_report.append(new_file_report)
    return new_report
