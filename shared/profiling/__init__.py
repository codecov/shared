import json
from typing import List

from cc_rustyribs import load_profiling_data


def load_profiling(summary_data: dict) -> "ProfilingSummaryDataAnalyzer":
    return ProfilingSummaryDataAnalyzer(summary_data)


class ProfilingSummaryDataAnalyzer(object):
    def __init__(self, summary_data):
        self._summary_data = summary_data

    def get_critical_files_filenames(self) -> List[str]:
        files_found_critical_so_far = set()
        files_found_critical_so_far.update(
            self._summary_data["file_groups"]["sum_of_executions"]["above_1_stdev"]
        )
        return sorted(files_found_critical_so_far)


class ProfilingDataFullAnalyzer(object):
    def __init__(self, analyzer):
        self._internal_analyzer = analyzer

    @classmethod
    def load_from_json(cls, json_data):
        return cls(load_profiling_data(json_data))

    def find_impacted_endpoints(self, base_report, head_report, diff):
        return json.loads(
            self._internal_analyzer.find_impacted_endpoints_json(
                base_report, head_report, diff
            )
        )
