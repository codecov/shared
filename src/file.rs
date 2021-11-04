use pyo3::prelude::*;
use serde::Serialize;
use std::collections::HashMap;

use crate::cov;
use crate::line;

#[pyclass]
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct FileTotals {
    #[pyo3(get)]
    pub hits: i32,
    #[pyo3(get)]
    pub misses: i32,
    #[pyo3(get)]
    pub partials: i32,
    #[pyo3(get)]
    pub branches: i32,
    pub sessions: i32,
    pub complexity: i32,
    pub complexity_total: i32,
    #[pyo3(get)]
    pub methods: i32,
}

#[pymethods]
impl FileTotals {
    #[getter(lines)]
    pub fn get_lines(&self) -> PyResult<i32> {
        Ok(self.get_line_count())
    }
}

impl FileTotals {
    pub fn get_line_count(&self) -> i32 {
        return self.hits + self.misses + self.partials;
    }

    pub fn new() -> FileTotals {
        FileTotals {
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
            methods: 0,
        }
    }

    pub fn is_empty(&self) -> bool {
        return self.get_line_count() == 0;
    }

    pub fn from_lines(lines: Vec<&line::ReportLine>) -> FileTotals {
        let mut res: FileTotals = FileTotals {
            hits: 0,
            misses: 0,
            methods: 0,
            partials: 0,
            branches: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for report_line in lines.iter() {
            match report_line.coverage {
                cov::Coverage::Hit => res.hits += 1,
                cov::Coverage::Miss => res.misses += 1,
                cov::Coverage::Partial(_) => res.partials += 1,
                cov::Coverage::Ignore => {}
            }
            match &report_line.complexity {
                Some(value) => match value {
                    line::Complexity::SingleComplexity(v) => {
                        res.complexity += v;
                    }
                    line::Complexity::TotalComplexity((n, d)) => {
                        res.complexity += n;
                        res.complexity_total += d;
                    }
                },
                None => {}
            }
            match report_line.coverage_type {
                line::CoverageType::Standard => {}
                line::CoverageType::Branch => res.branches += 1,
                line::CoverageType::Method => res.methods += 1,
            }
        }
        return res;
    }
}

pub struct ReportFile {
    pub lines: HashMap<i32, line::ReportLine>,
}

impl ReportFile {
    pub fn get_eof(&self) -> i32 {
        return match self.lines.keys().max() {
            Some(expr) => *expr + 1,
            None => 0,
        };
    }

    pub fn get_filtered_totals(&self, session_ids: &Vec<i32>) -> FileTotals {
        let all_lines: Vec<line::ReportLine> = self
            .lines
            .values()
            .filter_map(|x| x.filter_by_session_ids(session_ids))
            .collect();
        return FileTotals::from_lines(all_lines.iter().collect());
    }

    pub fn calculate_per_flag_totals(
        &self,
        flag_mapping: &HashMap<i32, Vec<String>>,
    ) -> HashMap<String, FileTotals> {
        let mut book_reviews: HashMap<String, FileTotals> = HashMap::new();
        for (_, report_line) in self.lines.iter() {
            for sess in &report_line.sessions {
                match flag_mapping.get(&sess.id) {
                    Some(flags) => {
                        for f in flags {
                            let mut stat =
                                book_reviews.entry(f.to_string()).or_insert(FileTotals {
                                    hits: 0,
                                    misses: 0,
                                    partials: 0,
                                    branches: 0,
                                    sessions: 0,
                                    complexity: 0,
                                    complexity_total: 0,
                                    methods: 0,
                                });
                            match sess.coverage {
                                cov::Coverage::Hit => stat.hits += 1,
                                cov::Coverage::Miss => stat.misses += 1,
                                cov::Coverage::Partial(_) => stat.partials += 1,
                                cov::Coverage::Ignore => {}
                            }
                        }
                    }
                    None => {}
                }
            }
        }
        return book_reviews;
    }

    pub fn get_totals(&self) -> FileTotals {
        return FileTotals::from_lines(self.lines.values().collect());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use fraction::GenericFraction;

    fn create_line_for_test(line_number: i32, coverage: cov::Coverage) -> (i32, line::ReportLine) {
        (
            line_number,
            line::ReportLine {
                coverage: coverage.clone(),
                coverage_type: line::CoverageType::Standard,
                sessions: vec![line::LineSession {
                    id: 0,
                    coverage: coverage,
                    complexity: None,
                }],
                complexity: None,
            },
        )
    }

    #[test]
    fn from_lines_empty() {
        let expected_result = FileTotals {
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
            methods: 0,
        };
        let result = FileTotals::from_lines(vec![]);
        assert_eq!(expected_result, result);
        assert_eq!(result.get_line_count(), 0);
    }

    #[test]
    fn from_lines_some() {
        let expected_result = FileTotals {
            hits: 1,
            misses: 1,
            partials: 1,
            branches: 1,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
            methods: 0,
        };
        let result = FileTotals::from_lines(vec![
            &line::ReportLine {
                coverage: cov::Coverage::Hit,
                coverage_type: line::CoverageType::Standard,
                sessions: vec![],
                complexity: None,
            },
            &line::ReportLine {
                coverage: cov::Coverage::Miss,
                coverage_type: line::CoverageType::Branch,
                sessions: vec![],
                complexity: None,
            },
            &line::ReportLine {
                coverage: cov::Coverage::Partial(GenericFraction::new(3, 10)),
                coverage_type: line::CoverageType::Standard,
                sessions: vec![],
                complexity: None,
            },
            &line::ReportLine {
                coverage: cov::Coverage::Ignore,
                coverage_type: line::CoverageType::Standard,
                sessions: vec![],
                complexity: None,
            },
        ]);
        assert_eq!(expected_result, result);
        assert_eq!(result.get_line_count(), 3);
    }

    #[test]
    fn get_eof_is_correct() {
        let file = ReportFile {
            lines: vec![
                create_line_for_test(101, cov::Coverage::Hit),
                create_line_for_test(103, cov::Coverage::Miss),
            ]
            .into_iter()
            .collect(),
        };
        assert_eq!(file.get_eof(), 104);
    }
}
