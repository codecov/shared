from shared.reports.types import Change
from shared import ribs


def _convert_diff_to_rust(diff):
    res = {}
    for name, data in diff["files"].items():
        segment_data = [
            (
                tuple([int(v) for v in seg["header"]]),
                [li[0] if li else " " for li in seg["lines"]],
            )
            for seg in data["segments"]
        ]
        res[name] = data["type"], data["before"], segment_data
    return res


def run_comparison_using_rust(base_report, head_report, diff):
    return ribs.run_comparison(
        base_report.rust_report.get_report(),
        head_report.rust_report.get_report(),
        _convert_diff_to_rust(diff),
    )


def get_changes_using_rust(base_report, head_report, diff):
    changes = []
    data = run_comparison_using_rust(base_report, head_report, diff)
    for d in data["files"]:
        if d["unexpected_line_changes"]:
            changes.append(
                Change(
                    path=d["base_name"],
                    in_diff=bool(d["added_diff_coverage"]),
                    old_path=diff.get("before") if diff else None,
                    totals=None,
                    new=(
                        d["head_coverage"] is not None
                        and d["base_coverage"] is None
                        and not d["file_was_added_by_diff"]
                    ),
                    deleted=(
                        d["base_coverage"] is not None
                        and d["head_coverage"] is None
                        and not d["file_was_removed_by_diff"]
                    ),
                )
            )
    return changes
