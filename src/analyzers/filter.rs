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
        let mut initial = report::ReportTotals::new();
        for filename in report.filenames.keys().filter(|x| self.should_include(x)) {
            if let Some(report_file) = report.get_by_filename(filename) {
                match &sessions {
                    Some(sess) => {
                        let some_totals = report_file.get_filtered_totals(&sess);
                        initial.add_up(&some_totals)
                    }
                    None => {
                        let some_totals = report_file.get_totals();
                        initial.add_up(&some_totals)
                    }
                };
            }
        }
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
            summary: file::FileTotals::from_lines(involved_lines.iter().map(|(n, x)| x).collect()),
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
