import json

from shared.rustyribs import (
    FilterAnalyzer,
    ProfilingData,
    SimpleAnalyzer,
    parse_report,
    run_comparison_as_json,
)


def run_comparison(*args, **kwargs):
    return json.loads(run_comparison_as_json(*args, **kwargs))


def load_profiling_data(data_string):
    return ProfilingData.load_from_json(data_string)


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
