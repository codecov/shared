use pyo3::prelude::*;
use std::collections::HashMap;

use crate::cov;
use crate::line;

#[pyclass]
#[derive(Debug, Clone)]
pub struct FileTotals {
    #[pyo3(get)]
    pub lines: i32,
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
    methods: i32,
}

impl FileTotals {
    pub fn new() -> FileTotals {
        FileTotals {
            lines: 0,
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
        return self.lines == 0;
    }

    pub fn from_lines(lines: Vec<&line::ReportLine>) -> FileTotals {
        let mut res: FileTotals = FileTotals {
            lines: 0,
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
            res.lines += 1;
            match report_line.coverage {
                cov::Coverage::Hit => res.hits += 1,
                cov::Coverage::Miss => res.misses += 1,
                cov::Coverage::Partial(_) => res.partials += 1,
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
            Some(expr) => *expr,
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
                                    lines: 0,
                                    hits: 0,
                                    misses: 0,
                                    partials: 0,
                                    branches: 0,
                                    sessions: 0,
                                    complexity: 0,
                                    complexity_total: 0,
                                    methods: 0,
                                });
                            stat.lines += 1;
                            match sess.coverage {
                                cov::Coverage::Hit => stat.hits += 1,
                                cov::Coverage::Miss => stat.misses += 1,
                                cov::Coverage::Partial(_) => stat.partials += 1,
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
