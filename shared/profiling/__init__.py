from typing import List


def load_profiling(summary_data: dict) -> "ProfilingDataAnalyzer":
    return ProfilingDataAnalyzer(summary_data)


class ProfilingDataAnalyzer(object):
    def __init__(self, summary_data):
        self._summary_data = summary_data

    def get_critical_files_filenames(self) -> List[str]:
        files_found_critical_so_far = set()
        files_found_critical_so_far.update(
            self._summary_data["file_groups"]["sum_of_executions"]["above_1_stdev"]
        )
        return sorted(files_found_critical_so_far)
