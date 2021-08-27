from shared.profiling import ProfilingDataAnalyzer, load_profiling


class TestProfilingDataAnalyzer(object):
    def test_load_profiling(self):
        res = load_profiling(
            {
                "general": {"total_profiled_files": 40},
                "file_groups": {
                    "sum_of_executions": {
                        "above_1_stdev": [
                            "path/file.py",
                            "secondfile.go",
                            "thirdfile.make",
                        ]
                    }
                },
            }
        )
        assert isinstance(res, ProfilingDataAnalyzer)

    def test_get_critical_files_filenames(self):
        analyzer = ProfilingDataAnalyzer(
            {
                "general": {"total_profiled_files": 40},
                "file_groups": {
                    "sum_of_executions": {
                        "above_1_stdev": [
                            "path/file.py",
                            "secondfile.go",
                            "thirdfile.make",
                        ]
                    }
                },
            }
        )
        assert analyzer.get_critical_files_filenames() == [
            "path/file.py",
            "secondfile.go",
            "thirdfile.make",
        ]
