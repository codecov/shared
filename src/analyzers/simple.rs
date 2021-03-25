use fraction::GenericFraction;
use std::collections::HashMap;
use std::collections::HashSet;
use std::iter::FromIterator;

use pyo3::prelude::*;

use crate::changes;
use crate::cov;
use crate::diff;
use crate::file;
use crate::line;
use crate::report;

#[pyclass]
pub struct SimpleAnalyzer {}

#[pymethods]
impl SimpleAnalyzer {
    #[new]
    fn new() -> Self {
        SimpleAnalyzer {}
    }

    pub fn get_totals(&self, report: &report::Report) -> PyResult<report::ReportTotals> {
        report.get_simple_totals()
    }

    pub fn calculate_diff(
        &self,
        report: &report::Report,
        diff: diff::DiffInput,
    ) -> (
        report::ReportTotals,
        HashMap<String, diff::FileDiffAnalysis>,
    ) {
        let mut res = report::ReportTotals::new();
        let mut mapping: HashMap<String, diff::FileDiffAnalysis> = HashMap::new();
        for (filename, diff_data) in diff.iter() {
            match report.get_by_filename(filename) {
                None => {}
                Some(file_report) => {
                    let file_res = self.calculate_reportfile_diff(file_report, diff_data);
                    res.add_up(&file_res.summary);
                    mapping.insert(filename.to_string(), file_res);
                }
            }
        }
        return (res, mapping);
    }

    pub fn get_changes(
        &self,
        base_report: &report::Report,
        head_report: &report::Report,
        diff: diff::DiffInput,
    ) -> Vec<changes::Change> {
        let mut changes_list = Vec::new();
        let base_filenames: HashSet<String> =
            HashSet::from_iter(base_report.report_files.keys().map(|f| f.clone()));
        let head_filenames: HashSet<String> =
            HashSet::from_iter(head_report.report_files.keys().map(|f| f.clone()));
        let files_in_diff: HashSet<String> = HashSet::from_iter(diff.keys().map(|f| f.clone()));
        let files_that_were_moved: HashSet<String> = HashSet::from_iter(
            diff.values()
                .filter_map(|(_, b, _)| b.as_ref())
                .map(|f| f.clone()),
        );
        let files_that_went_somewhere: HashSet<_> =
            files_in_diff.union(&files_that_were_moved).collect();
        let originally_missing_files: HashSet<_> =
            base_filenames.difference(&head_filenames).collect();
        let originally_new_filenames: HashSet<_> =
            head_filenames.difference(&base_filenames).collect();
        let missing_files: HashSet<_> = originally_missing_files
            .difference(&files_that_went_somewhere)
            .collect();
        let mut new_filenames: HashSet<String> = originally_new_filenames
            .difference(&files_that_went_somewhere)
            .map(|x| x.to_string())
            .collect();
        for (filename, new_file) in head_report.report_files.iter() {
            let diff_data = diff.get(filename);
            if !(&new_filenames.contains(filename)) {
                let original_name: String = match diff_data {
                    Some(x) => match &x.1 {
                        None => filename.to_string(),
                        Some(o) => o.to_string(),
                    },
                    None => filename.to_string(),
                };
                match base_report.get_by_filename(&original_name) {
                    None => {
                        new_filenames.insert(original_name);
                    }
                    Some(old_file) => {
                        match self.get_filereport_changes(
                            old_file,
                            new_file,
                            filename,
                            &original_name,
                            diff_data,
                        ) {
                            Some(x) => {
                                changes_list.push(x);
                            }
                            None => {}
                        }
                    }
                }
            }
        }
        for filename in missing_files {
            changes_list.push(changes::Change {
                path: filename.to_string(),
                deleted: true,
                new: false,
                in_diff: false,
                old_path: None,
                totals: None,
            })
        }

        for filename in new_filenames {
            changes_list.push(changes::Change {
                path: filename.to_string(),
                new: true,
                deleted: false,
                in_diff: false,
                old_path: None,
                totals: None,
            })
        }
        return changes_list;
    }
}

impl SimpleAnalyzer {
    fn calculate_reportfile_diff(
        &self,
        reportfile: &file::ReportFile,
        diff_data: &(
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
    ) -> diff::FileDiffAnalysis {
        let (_, lines_on_head) = diff::get_exclusions_from_diff(Some(&diff_data.2));
        let mut involved_lines: Vec<&line::ReportLine> = Vec::new();
        let mut involved_coverages = Vec::new();
        for line_number in lines_on_head.iter() {
            match reportfile.lines.get(line_number) {
                None => {}
                Some(line) => {
                    involved_lines.push(line);
                    involved_coverages.push((*line_number, &line.coverage))
                }
            }
        }
        return diff::FileDiffAnalysis {
            summary: file::FileTotals::from_lines(involved_lines),
            lines_with_hits: involved_coverages
                .iter()
                .filter_map(|(line_number, cov)| match cov {
                    cov::Coverage::Hit => Some(*line_number),
                    _ => None,
                })
                .collect(),
            lines_with_misses: involved_coverages
                .iter()
                .filter_map(|(line_number, cov)| match cov {
                    cov::Coverage::Miss => Some(*line_number),
                    _ => None,
                })
                .collect(),
            lines_with_partials: involved_coverages
                .iter()
                .filter_map(|(line_number, cov)| match cov {
                    cov::Coverage::Partial(_) => Some(*line_number),
                    _ => None,
                })
                .collect(),
        };
    }

    fn get_filereport_changes(
        &self,
        base_report: &file::ReportFile,
        head_report: &file::ReportFile,
        filename: &str,
        original_name: &str,
        diff: Option<&diff::FileDiffData>,
    ) -> Option<changes::Change> {
        let (only_on_base, only_on_head) = diff::get_exclusions_from_diff(match diff {
            None => None,
            Some(x) => Some(&x.2),
        });
        let mut head_coverages: Vec<&cov::Coverage> = Vec::new();
        let mut base_coverages: Vec<&cov::Coverage> = Vec::new();
        let mut current_base: i32 = 0;
        let mut current_head: i32 = 0;
        let base_eof = base_report.get_eof();
        let head_eof = head_report.get_eof();
        while current_base < base_eof || current_head < head_eof {
            current_base += 1;
            current_head += 1;
            while only_on_base.contains(&current_base) {
                current_base += 1;
            }
            while only_on_head.contains(&current_head) {
                current_head += 1
            }
            match base_report.lines.get(&current_base) {
                Some(base_line) => match head_report.lines.get(&current_head) {
                    None => {
                        base_coverages.push(&base_line.coverage);
                    }
                    Some(head_line) => {
                        if head_line.coverage != base_line.coverage {
                            head_coverages.push(&head_line.coverage);
                            base_coverages.push(&base_line.coverage);
                        }
                    }
                },
                None => match head_report.lines.get(&current_head) {
                    None => {}
                    Some(head_line) => {
                        head_coverages.push(&head_line.coverage);
                    }
                },
            }
        }
        if head_coverages.is_empty() && base_coverages.is_empty() {
            return None;
        }
        let (head_hits, head_misses, head_partials) =
            head_coverages
                .iter()
                .fold((0, 0, 0), |(hits, misses, partials), x| match x {
                    cov::Coverage::Hit => (hits + 1, misses, partials),
                    cov::Coverage::Miss => (hits, misses + 1, partials),
                    cov::Coverage::Partial(_) => (hits, misses, partials + 1),
                });

        let (base_hits, base_misses, base_partials) =
            base_coverages
                .iter()
                .fold((0, 0, 0), |(hits, misses, partials), x| match x {
                    cov::Coverage::Hit => (hits + 1, misses, partials),
                    cov::Coverage::Miss => (hits, misses + 1, partials),
                    cov::Coverage::Partial(_) => (hits, misses, partials + 1),
                });
        let hits = head_hits - base_hits;
        let misses = head_misses - base_misses;
        let partials = head_partials - base_partials;
        let base_totals = base_report.get_totals();
        Some(changes::Change {
            path: filename.to_string(),
            new: false,
            deleted: false,
            in_diff: diff.is_some(),
            old_path: if original_name == filename {
                None
            } else {
                Some(original_name.to_string())
            },
            totals: Some(changes::ChangeStats {
                hits,
                misses,
                partials,
                changed_coverage: GenericFraction::new(
                    hits + base_totals.hits,
                    partials + misses + base_totals.partials + base_totals.misses,
                ),
            }),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_totals_works() {
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
                            branches: 0,
                            partials: vec![],
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
                                branches: 0,
                                partials: vec![],
                                complexity: None,
                            },
                            line::LineSession {
                                id: 1,
                                coverage: cov::Coverage::Partial(GenericFraction::new(1, 2)),
                                branches: 0,
                                partials: vec![],
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
        let analyzer_unit = SimpleAnalyzer {};
        let unit_res = analyzer_unit.get_totals(&report).unwrap();
        assert_eq!(unit_res.files, 1);
        assert_eq!(unit_res.lines, 2);
        assert_eq!(unit_res.hits, 2);
        assert_eq!(unit_res.misses, 0);
        assert_eq!(unit_res.partials, 0);
    }
}
