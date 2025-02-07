import logging
import re
from typing import Mapping, Sequence

from shared.reports.editable import EditableReport
from shared.reports.resources import Report
from shared.utils.match import Matcher
from shared.utils.sessions import SessionType

log = logging.getLogger(__name__)


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
            return re.sub(
                regex, f"CF[{number_so_far + 1}]", original_session_name, count=1
            )
    return f"CF[1] - {original_session_name}"


def generate_carryforward_report(
    report: Report,
    flags: Sequence[str],
    paths: Sequence[str],
    session_extras: Mapping[str, str] | None = None,
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
    new_report = EditableReport(
        chunks=report._chunks,
        files=report._files,
        sessions=report.sessions,
        totals=None,
    )
    if paths:
        matcher = Matcher(paths)
        for filename in new_report.files:
            if not matcher.match(filename):
                del new_report[filename]
    sessions_to_delete = []
    for sid, session in new_report.sessions.items():
        if not contain_any_of_the_flags(flags, session.flags):
            sessions_to_delete.append(int(sid))
        else:
            session.session_extras = session_extras or session.session_extras
            session.name = carriedforward_session_name(session.name)
            session.session_type = SessionType.carriedforward
    log.info(
        "Removing sessions that are not supposed to carryforward",
        extra=dict(deleted_sessions=sessions_to_delete),
    )
    new_report.delete_multiple_sessions(sessions_to_delete)
    return new_report


def contain_any_of_the_flags(expected_flags, actual_flags):
    if expected_flags is None or actual_flags is None:
        return False
    return len(set(expected_flags) & set(actual_flags)) > 0
