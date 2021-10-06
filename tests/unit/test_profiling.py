import json
from pathlib import Path

import pytest

from shared.profiling import (
    ProfilingDataFullAnalyzer,
    ProfilingSummaryDataAnalyzer,
    load_profiling,
)
from shared.reports.readonly import ReadOnlyReport
from shared.reports.resources import (
    LineSession,
    Report,
    ReportFile,
    ReportLine,
    Session,
)
from shared.ribs import rustify_diff

here = Path(__file__)


@pytest.fixture
def sample_open_telemetry_collected_as_str():
    with open(
        here.parent.parent / "samples/sample_opentelem_collected.json", "r"
    ) as file:
        return file.read()


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
        assert isinstance(res, ProfilingSummaryDataAnalyzer)

    def test_get_critical_files_filenames(self):
        analyzer = ProfilingSummaryDataAnalyzer(
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


class TestProfilingFullDataAnalyzer(object):
    def test_find_impacted_endpoints(self, mocker):
        a = ProfilingDataFullAnalyzer(
            mocker.MagicMock(
                find_impacted_endpoints=mocker.MagicMock(
                    return_value=json.dumps(
                        [
                            {
                                "files": [
                                    {
                                        "filename": "helpers/logging_config.py",
                                        "impacted_base_lines": [1],
                                    }
                                ],
                                "group_name": "run/app.tasks.upload.Upload",
                            },
                            {
                                "files": [
                                    {
                                        "filename": "helpers/logging_config.py",
                                        "impacted_base_lines": [98],
                                    }
                                ],
                                "group_name": "run/app.tasks.upload_processor.UploadProcessorTask",
                            },
                        ]
                    )
                )
            )
        )
        expected_result = [
            {
                "files": [
                    {
                        "filename": "helpers/logging_config.py",
                        "impacted_base_lines": [1],
                    }
                ],
                "group_name": "run/app.tasks.upload.Upload",
            },
            {
                "files": [
                    {
                        "filename": "helpers/logging_config.py",
                        "impacted_base_lines": [98],
                    }
                ],
                "group_name": "run/app.tasks.upload_processor.UploadProcessorTask",
            },
        ]
        res = a.find_impacted_endpoints(
            mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(),
        )
        assert res == expected_result

    def test_load_real_data_and_find_endpoints(
        self, sample_open_telemetry_collected_as_str
    ):
        a = ProfilingDataFullAnalyzer.load_from_json(
            sample_open_telemetry_collected_as_str
        )
        assert isinstance(a, ProfilingDataFullAnalyzer)
        assert hasattr(a, "_internal_analyzer")
