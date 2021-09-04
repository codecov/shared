from shared.reports.types import Change
from shared import ribs


def rustify_diff(diff):
    if diff is None or "files" not in diff:
        return {}
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


def run_comparison_using_rust(base_report, head_report, diff):
    return ribs.run_comparison(
        base_report.rust_report.get_report(),
        head_report.rust_report.get_report(),
        rustify_diff(diff),
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
