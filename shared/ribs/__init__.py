import json

from shared.rustyribs import (
    parse_report,
    FilterAnalyzer,
    SimpleAnalyzer,
    run_comparison_as_json,
)


def run_comparison(*args, **kwargs):
    return json.loads(run_comparison_as_json(*args, **kwargs))
