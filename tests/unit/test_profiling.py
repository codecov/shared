import json
from pathlib import Path

import pytest
from cc_rustyribs import rustify_diff

from shared.profiling import (
    ProfilingDataFullAnalyzer,
    ProfilingSummaryDataAnalyzer,
    load_profiling,
)
from shared.reports.readonly import ReadOnlyReport
from shared.reports.resources import (
    Report,
    ReportFile,
    ReportLine,
    Session,
)
from shared.reports.types import LineSession

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
                find_impacted_endpoints_json=mocker.MagicMock(
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
            mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()
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
        base_report = Report()
        head_report = Report()
        first_file = ReportFile("helpers/logging_config.py")
        second_file = ReportFile("file_2.go")
        third_file = ReportFile("location/file_1.py")
        first_file.append(
            1,
            ReportLine.create(
                coverage=1,
                sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
            ),
        )
        first_file.append(
            12,
            ReportLine.create(
                coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]
            ),
        )
        first_file.append(
            13,
            ReportLine.create(
                coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]
            ),
        )
        first_file.append(
            14,
            ReportLine.create(
                coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]
            ),
        )
        first_file.append(
            6,
            ReportLine.create(
                coverage="1/2",
                sessions=[
                    LineSession(0, "1/2"),
                    LineSession(1, 0),
                    LineSession(2, "1/4"),
                ],
            ),
        )
        second_file.append(12, ReportLine.create(coverage=1, sessions=[[0, 1]]))
        second_file.append(
            51, ReportLine.create(coverage="1/2", type="b", sessions=[[0, "1/2"]])
        )
        third_file.append(
            100, ReportLine.create(coverage="1/2", type="b", sessions=[[3, "1/2"]])
        )
        third_file.append(
            101,
            ReportLine.create(
                coverage="1/2", type="b", sessions=[[2, "1/2"], [3, "1/2"]]
            ),
        )
        base_report.append(first_file)
        base_report.append(second_file)
        base_report.append(third_file)
        base_report.add_session(Session(id=0, flags=["simple"]))
        base_report.add_session(Session(id=1, flags=["complex"]))
        base_report.add_session(Session(id=2, flags=["complex", "simple"]))
        base_report.add_session(Session(id=3, flags=[]))
        diff = {
            "files": {
                "a.txt": {
                    "type": "new",
                    "before": None,
                    "segments": [{"header": ["0", "0", "1", ""], "lines": ["+banana"]}],
                    "stats": {"added": 1, "removed": 0},
                },
                "helpers/logging_config.py": {
                    "type": "modified",
                    "before": None,
                    "segments": [
                        {
                            "header": ["10", "7", "10", "7"],
                            "lines": [
                                "     if len(this_string) == 20:",
                                "         return True",
                                "     if len(set(this_string)) == 7:",
                                '-        print("0043")',
                                '+        print("0044")',
                                '         "',
                                "         return True",
                                "     return False",
                            ],
                        }
                    ],
                    "stats": {"added": 1, "removed": 1},
                },
            }
        }
        expected_result = [
            {
                "files": [
                    {
                        "filename": "helpers/logging_config.py",
                        "impacted_base_lines": [13],
                    }
                ],
                "group_name": "run/app.tasks.upload.Upload",
            },
            {
                "files": [
                    {
                        "filename": "helpers/logging_config.py",
                        "impacted_base_lines": [13],
                    }
                ],
                "group_name": "run/app.tasks.upload_processor.UploadProcessorTask",
            },
        ]
        res = a.find_impacted_endpoints(
            ReadOnlyReport.create_from_report(base_report).rust_report.get_report(),
            ReadOnlyReport.create_from_report(head_report).rust_report.get_report(),
            rustify_diff(diff),
        )
        assert res == expected_result
