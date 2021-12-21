use pyo3::prelude::*;

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
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cov;
    use crate::file;
    use crate::line;
    use fraction::GenericFraction;

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
        let analyzer_unit = SimpleAnalyzer {};
        let unit_res = analyzer_unit.get_totals(&report).unwrap();
        assert_eq!(unit_res.files, 1);
        assert_eq!(unit_res.lines, 2);
        assert_eq!(unit_res.hits, 2);
        assert_eq!(unit_res.misses, 0);
        assert_eq!(unit_res.partials, 0);
    }
}
