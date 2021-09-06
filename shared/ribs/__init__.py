import json

from shared.rustyribs import (
    FilterAnalyzer,
    SimpleAnalyzer,
    parse_report,
    run_comparison_as_json,
)


def run_comparison(*args, **kwargs):
    return json.loads(run_comparison_as_json(*args, **kwargs))
