use std::collections::HashMap;
use std::collections::HashSet;

use pyo3::prelude::*;

use crate::cov;
use crate::diff;
use crate::file;
use crate::line;
use crate::report;

#[pyclass]
pub struct FilterAnalyzer {
    files: Option<HashSet<String>>,
    flags: Option<Vec<String>>,
}

#[pymethods]
impl FilterAnalyzer {
    #[new]
    fn new(files: Option<HashSet<String>>, flags: Option<Vec<String>>) -> Self {
        FilterAnalyzer { files, flags }
    }

    pub fn get_totals(&self, report: &report::Report) -> PyResult<report::ReportTotals> {
        let sessions = match &self.flags {
            Some(actual_flags) => Some(report.get_sessions_from_flags(&actual_flags)),
            None => None,
        };
        let session_count: i32;
        let mut initial = report::ReportTotals::new();
        match &sessions {
            Some(sess) => {
                session_count = sess.len() as i32;
                let filtered_totals: Vec<file::FileTotals> = report
                    .report_files
                    .iter()
                    .filter(|(x, _)| self.should_include(x))
                    .map(|(_, y)| y.get_filtered_totals(sess))
                    .collect();
                for t in filtered_totals {
                    initial.add_up(&t);
                }
            }
            None => {
                session_count = report.session_mapping.len() as i32;
                let filtered_totals: Vec<file::FileTotals> = report
                    .report_files
                    .iter()
                    .filter(|(x, _)| self.should_include(x))
                    .map(|(_, y)| y.get_totals())
                    .collect();
                for t in filtered_totals {
                    initial.add_up(&t);
                }
            }
        };
        initial.sessions = session_count;
        return Ok(initial);
    }

    pub fn should_include(&self, filename: &str) -> bool {
        match &self.files {
            Some(f) => return f.contains(filename),
            None => return true,
        }
    }

    pub fn calculate_diff(
        &self,
        report: &report::Report,
        diff: diff::DiffInput,
    ) -> (
        report::ReportTotals,
        HashMap<String, diff::FileDiffAnalysis>,
    ) {
        let sessions = match &self.flags {
            Some(actual_flags) => Some(report.get_sessions_from_flags(&actual_flags)),
            None => None,
        };
        let mut res = report::ReportTotals::new();
        let mut mapping: HashMap<String, diff::FileDiffAnalysis> = HashMap::new();
        for (filename, diff_data) in diff.iter() {
            if self.should_include(filename) {
                match report.get_by_filename(filename) {
                    None => {}
                    Some(file_report) => {
                        let file_res =
                            self.calculate_reportfile_diff(file_report, diff_data, &sessions);
                        res.add_up(&file_res.summary);
                        mapping.insert(filename.to_string(), file_res);
                    }
                }
            }
        }
        return (res, mapping);
    }
}

impl FilterAnalyzer {
    fn calculate_reportfile_diff(
        &self,
        reportfile: &file::ReportFile,
        diff_data: &(
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
        sessions: &Option<Vec<i32>>,
    ) -> diff::FileDiffAnalysis {
        let (_, lines_on_head) = diff::get_exclusions_from_diff(Some(&diff_data.2));
        let mut involved_lines: Vec<(i32, line::ReportLine)> = Vec::new();
        for line_number in lines_on_head.iter() {
            match reportfile.lines.get(line_number) {
                None => {}
                Some(line) => {
                    let possible_filtered_line = match sessions {
                        Some(sess) => line.filter_by_session_ids(sess),
                        None => Some(line.clone()),
                    };
                    match possible_filtered_line {
                        Some(calculated_line) => {
                            involved_lines.push((*line_number, calculated_line));
                        }
                        None => {}
                    }
                }
            }
        }
        let res = diff::FileDiffAnalysis {
            summary: file::FileTotals::from_lines(involved_lines.iter().map(|(_, x)| x).collect()),
            lines_with_hits: involved_lines
                .iter()
                .filter_map(|(line_number, line)| match line.coverage {
                    cov::Coverage::Hit => Some(*line_number),
                    _ => None,
                })
                .collect(),
            lines_with_misses: involved_lines
                .iter()
                .filter_map(|(line_number, line)| match line.coverage {
                    cov::Coverage::Miss => Some(*line_number),
                    _ => None,
                })
                .collect(),
            lines_with_partials: involved_lines
                .iter()
                .filter_map(|(line_number, line)| match line.coverage {
                    cov::Coverage::Partial(_) => Some(*line_number),
                    _ => None,
                })
                .collect(),
        };
        return res;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use fraction::GenericFraction;

    #[test]
    fn filtered_totals_works() {
        let first_file = file::ReportFile {
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
        let report = report::Report {
            report_files: vec![
                ("file1.go".to_string(), first_file),
                (
                    "file_p.py".to_string(),
                    file::ReportFile {
                        lines: vec![].into_iter().collect(),
                    },
                ),
                (
                    "plo.c".to_string(),
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
        let analyzer_unit = FilterAnalyzer {
            files: Some(vec!["file1.go".to_string()].into_iter().collect()),
            flags: Some(vec!["unit".to_string()]),
        };
        let unit_res = analyzer_unit.get_totals(&report).unwrap();
        assert_eq!(unit_res.files, 1);
        assert_eq!(unit_res.lines, 2);
        assert_eq!(unit_res.hits, 2);
        assert_eq!(unit_res.misses, 0);
        assert_eq!(unit_res.partials, 0);
        assert_eq!(unit_res.sessions, 1);
        let analyzer_integration = FilterAnalyzer {
            files: Some(vec!["file1.go".to_string()].into_iter().collect()),
            flags: Some(vec!["integration".to_string()]),
        };
        let integration_res = analyzer_integration.get_totals(&report).unwrap();
        assert_eq!(integration_res.files, 1);
        assert_eq!(integration_res.lines, 1);
        assert_eq!(integration_res.hits, 0);
        assert_eq!(integration_res.misses, 0);
        assert_eq!(integration_res.partials, 1);
        assert_eq!(integration_res.sessions, 1);
        let analyzer_unit_and_integration = FilterAnalyzer {
            files: Some(vec!["file1.go".to_string()].into_iter().collect()),
            flags: Some(vec!["integration".to_string(), "unit".to_string()]),
        };
        let integration_and_unit_res = analyzer_unit_and_integration.get_totals(&report).unwrap();
        assert_eq!(integration_and_unit_res.files, 1);
        assert_eq!(integration_and_unit_res.lines, 2);
        assert_eq!(integration_and_unit_res.hits, 2);
        assert_eq!(integration_and_unit_res.misses, 0);
        assert_eq!(integration_and_unit_res.partials, 0);
        assert_eq!(integration_and_unit_res.sessions, 2);
        let analyzer_apple_and_banana = FilterAnalyzer {
            files: Some(vec!["file1.go".to_string()].into_iter().collect()),
            flags: Some(vec!["banana".to_string(), "apple".to_string()]),
        };
        let apple_and_banana_res = analyzer_apple_and_banana.get_totals(&report).unwrap();
        assert_eq!(apple_and_banana_res.files, 0);
        assert_eq!(apple_and_banana_res.lines, 0);
        assert_eq!(apple_and_banana_res.hits, 0);
        assert_eq!(apple_and_banana_res.misses, 0);
        assert_eq!(apple_and_banana_res.partials, 0);
        assert_eq!(apple_and_banana_res.sessions, 0);
    }

    #[test]
    fn filtered_totals_without_flags_works() {
        let first_file = file::ReportFile {
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
        let report = report::Report {
            report_files: vec![
                ("file1.go".to_string(), first_file),
                (
                    "file_p.py".to_string(),
                    file::ReportFile {
                        lines: vec![].into_iter().collect(),
                    },
                ),
                (
                    "plo.c".to_string(),
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
        let analyzer = FilterAnalyzer {
            files: Some(vec!["file1.go".to_string()].into_iter().collect()),
            flags: None,
        };
        let unit_res = analyzer.get_totals(&report).unwrap();
        assert_eq!(unit_res.files, 1);
        assert_eq!(unit_res.lines, 2);
        assert_eq!(unit_res.hits, 2);
        assert_eq!(unit_res.misses, 0);
        assert_eq!(unit_res.partials, 0);
        assert_eq!(unit_res.sessions, 2);
    }
}
