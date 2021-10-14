use crate::changes;
use crate::diff;
use crate::report;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use pyo3::types::PyType;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::collections::HashSet;

#[derive(Debug, Serialize)]
struct GroupImpact {
    files: Vec<GroupFileImpact>,
    group_name: String,
}

#[derive(Debug, Serialize)]
struct GroupFileImpact {
    filename: String,
    impacted_base_lines: Vec<i32>,
}

#[derive(Serialize, Deserialize, Debug)]
struct SingleFileProfilingData {
    filename: String,
    ln_ex_ct: Vec<(i32, i32)>,
}

#[derive(Serialize, Deserialize, Debug)]
struct SingleGroupProfilingData {
    count: i32,
    group_name: String,
    files: Vec<SingleFileProfilingData>,
}

impl SingleGroupProfilingData {
    fn find_impacted_endpoints(
        &self,
        files: &Vec<changes::FileChangesAnalysis>,
    ) -> Option<GroupImpact> {
        let inside_group_file_mapping: HashMap<String, &SingleFileProfilingData> = self
            .files
            .iter()
            .map(|k| (k.filename.to_owned(), k))
            .collect();
        let files_impacts: Vec<GroupFileImpact> = files
            .iter()
            .map(|file_change_data| {
                match inside_group_file_mapping.get(&file_change_data.base_name) {
                    Some(file_profiling_data) => {
                        let profiling_lines: HashSet<i32> = file_profiling_data
                            .ln_ex_ct
                            .iter()
                            .map(|(ln, _)| *ln)
                            .collect();
                        let changed_lines: HashSet<i32> =
                            match &file_change_data.removed_diff_coverage {
                                Some(removed_lines) => {
                                    removed_lines.iter().map(|(ln, _)| *ln).collect()
                                }
                                None => HashSet::new(),
                            };
                        let impacted_lines: Vec<i32> = profiling_lines
                            .intersection(&changed_lines)
                            .map(|x| *x)
                            .collect();
                        if !impacted_lines.is_empty() {
                            Some(GroupFileImpact {
                                filename: file_change_data.base_name.to_owned(),
                                impacted_base_lines: impacted_lines,
                            })
                        } else {
                            None
                        }
                    }
                    None => None,
                }
            })
            .filter_map(|x| x)
            .collect();
        if files_impacts.is_empty() {
            return None;
        }
        return Some(GroupImpact {
            group_name: self.group_name.to_owned(),
            files: files_impacts,
        });
    }
}

#[pyclass]
pub struct ProfilingData {
    groups: Vec<SingleGroupProfilingData>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ProfilingDataJson {
    files: Vec<SingleFileProfilingData>,
    groups: Vec<SingleGroupProfilingData>,
}

#[pymethods]
impl ProfilingData {
    #[classmethod]
    pub fn load_from_json(_cls: &PyType, json_str: &str) -> PyResult<ProfilingData> {
        let json_data: Result<ProfilingDataJson, _> = serde_json::from_str(json_str);
        match json_data {
            Ok(result) => {
                return Ok(ProfilingData {
                    groups: result.groups,
                })
            }
            Err(_) => Err(PyException::new_err("Error loading full profiling data")),
        }
    }

    fn find_impacted_endpoints_json(
        &self,
        base_report: &report::Report,
        head_report: &report::Report,
        diff: diff::DiffInput,
    ) -> PyResult<String> {
        let res = self.find_impacted_endpoints(base_report, head_report, diff);
        return match serde_json::to_string(&res) {
            Ok(value) => Ok(value),
            Err(_) => Err(PyException::new_err("Error serializing impact")),
        };
    }

    fn apply_diff_changes(&mut self, _diff: diff::DiffInput) {}
}

impl ProfilingData {
    fn find_impacted_endpoints(
        &self,
        base_report: &report::Report,
        head_report: &report::Report,
        diff: diff::DiffInput,
    ) -> Vec<GroupImpact> {
        let k = changes::run_comparison_analysis(base_report, head_report, &diff);
        return self
            .groups
            .iter()
            .map(|group| group.find_impacted_endpoints(&k.files))
            .filter_map(|x| x)
            .collect();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cov;
    use crate::file;
    use crate::line;
    use fraction::GenericFraction;
    use std::fs::File;
    use std::io::Read;

    #[test]
    fn it_parses_data() {
        let mut contents = String::new();
        let mut file =
            File::open("tests/samples/sample_opentelem_collected.json").expect("file not there");
        file.read_to_string(&mut contents);
        let v: ProfilingDataJson = serde_json::from_str(&contents).expect("Not a valid json stuff");
        let filenames: Vec<String> = v.files.iter().map(|f| f.filename.to_owned()).collect();
        assert_eq!(
            filenames,
            vec![
                "helpers/logging_config.py",
                "services/redis.py",
                "tasks/base.py",
                "tasks/upload.py",
                "database/base.py",
                "database/engine.py",
                "database/models/core.py",
                "database/models/reports.py",
                "helpers/cache.py",
                "helpers/pathmap/pathmap.py",
                "helpers/pathmap/tree.py",
                "services/archive.py",
                "services/bots.py",
                "services/repository.py",
                "services/storage.py",
                "services/path_fixer/__init__.py",
                "services/path_fixer/fixpaths.py",
                "services/path_fixer/user_path_fixes.py",
                "services/path_fixer/user_path_includes.py",
                "services/report/__init__.py",
                "services/report/parser.py",
                "services/report/raw_upload_processor.py",
                "services/report/report_processor.py",
                "services/report/languages/base.py",
                "services/report/languages/clover.py",
                "services/report/languages/cobertura.py",
                "services/report/languages/csharp.py",
                "services/report/languages/helpers.py",
                "services/report/languages/jacoco.py",
                "services/report/languages/jetbrainsxml.py",
                "services/report/languages/mono.py",
                "services/report/languages/scoverage.py",
                "services/report/languages/vb.py",
                "services/report/languages/vb2.py",
                "services/yaml/reader.py",
                "tasks/upload_processor.py"
            ]
        );
    }

    #[test]
    fn it_calculates_impacted_endpoints_correctly() {
        let v: ProfilingData = ProfilingData {
            groups: vec![SingleGroupProfilingData {
                count: 10,
                group_name: "GET /data".to_string(),
                files: vec![SingleFileProfilingData {
                    filename: "file1.go".to_string(),
                    ln_ex_ct: vec![(1, 10), (2, 8)],
                }],
            }],
        };
        let first_file_head = file::ReportFile {
            lines: vec![
                (
                    1,
                    line::ReportLine {
                        coverage: cov::Coverage::Hit,
                        coverage_type: line::CoverageType::Standard,
                        sessions: vec![line::LineSession {
                            id: 0,
                            coverage: cov::Coverage::Hit,
                            complexity: None,
                        }],
                        complexity: None,
                    },
                ),
                (
                    2,
                    line::ReportLine {
                        coverage: cov::Coverage::Hit,
                        coverage_type: line::CoverageType::Standard,
                        sessions: vec![
                            line::LineSession {
                                id: 0,
                                coverage: cov::Coverage::Hit,
                                complexity: None,
                            },
                            line::LineSession {
                                id: 1,
                                coverage: cov::Coverage::Partial(GenericFraction::new(1, 2)),
                                complexity: None,
                            },
                        ],
                        complexity: None,
                    },
                ),
            ]
            .into_iter()
            .collect(),
        };
        let first_file_base = file::ReportFile {
            lines: vec![
                (
                    1,
                    line::ReportLine {
                        coverage: cov::Coverage::Miss,
                        coverage_type: line::CoverageType::Standard,
                        sessions: vec![line::LineSession {
                            id: 0,
                            coverage: cov::Coverage::Miss,
                            complexity: None,
                        }],
                        complexity: None,
                    },
                ),
                (
                    2,
                    line::ReportLine {
                        coverage: cov::Coverage::Hit,
                        coverage_type: line::CoverageType::Standard,
                        sessions: vec![
                            line::LineSession {
                                id: 0,
                                coverage: cov::Coverage::Hit,
                                complexity: None,
                            },
                            line::LineSession {
                                id: 1,
                                coverage: cov::Coverage::Partial(GenericFraction::new(1, 2)),
                                complexity: None,
                            },
                        ],
                        complexity: None,
                    },
                ),
            ]
            .into_iter()
            .collect(),
        };
        let head_report = report::Report {
            report_files: vec![
                ("file1.go".to_string(), first_file_head),
                (
                    "file_p.py".to_string(),
                    file::ReportFile {
                        lines: vec![].into_iter().collect(),
                    },
                ),
            ]
            .into_iter()
            .collect(),
            session_mapping: vec![
                (0, vec!["unit".to_string()]),
                (1, vec!["integration".to_string()]),
            ]
            .into_iter()
            .collect(),
        };
        let base_report = report::Report {
            report_files: vec![
                ("file1.go".to_string(), first_file_base),
                (
                    "file_p.py".to_string(),
                    file::ReportFile {
                        lines: vec![].into_iter().collect(),
                    },
                ),
            ]
            .into_iter()
            .collect(),
            session_mapping: vec![
                (0, vec!["unit".to_string()]),
                (1, vec!["integration".to_string()]),
            ]
            .into_iter()
            .collect(),
        };
        let diffinput: diff::DiffInput = vec![(
            "file1.go".to_string(),
            (
                "changed".to_string(),
                None,
                vec![((1, 1, 1, 1), vec!["-".to_string(), "+".to_string()])],
            ),
        )]
        .into_iter()
        .collect();
        let res = v.find_impacted_endpoints(&base_report, &head_report, diffinput);
        assert_eq!(res.len(), 1);
        assert_eq!(res[0].group_name, "GET /data");
        assert_eq!(res[0].files.len(), 1);
        assert_eq!(res[0].files[0].filename, "file1.go".to_string());
        assert_eq!(res[0].files[0].impacted_base_lines, vec![1]);
    }
}
