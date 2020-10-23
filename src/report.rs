use crate::cov;
use crate::line;
use crate::file;

use pyo3::prelude::*;

use fraction::GenericFraction;
use std::collections::HashMap;
use std::collections::HashSet;

#[pyclass]
#[derive(Debug)]
pub struct ReportTotals {
    #[pyo3(get)]
    pub files: i32,
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

impl ReportTotals {
    pub fn new() -> ReportTotals {
        ReportTotals {
            files: 0,
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

    pub fn from_lines(lines: Vec<&line::ReportLine>) -> ReportTotals {
        let mut res: ReportTotals = ReportTotals {
            files: 1,
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

impl ReportTotals {
    pub fn add_up(&mut self, other: &file::FileTotals) {
        self.files += 1;
        self.lines += other.lines;
        self.hits += other.hits;
        self.misses += other.misses;
        self.partials += other.partials;
        self.branches += other.branches;
        self.sessions += other.sessions;
        self.complexity += other.complexity;
        self.complexity_total += other.complexity_total;
    }
}

#[pymethods]
impl ReportTotals {
    #[getter(coverage)]
    pub fn get_coverage(&self) -> PyResult<Option<String>> {
        if self.lines == 0 {
            return Ok(None);
        }
        if self.hits == self.lines {
            return Ok(Some("100".to_string()));
        }
        if self.hits == 0 {
            return Ok(Some("0".to_string()));
        }
        let fraction: GenericFraction<i32> = GenericFraction::new(100 * self.hits, self.lines);
        Ok(Some(format!("{:.1$}", fraction, 5)))
    }

    #[getter(complexity)]
    fn get_complexity(&self) -> PyResult<Option<i32>> {
        if self.lines == 0 {
            return Ok(None);
        }
        return Ok(Some(self.complexity));
    }
}

#[pyclass]
pub struct Report {
    pub filenames: HashMap<String, i32>,
    pub report_files: Vec<file::ReportFile>,
    pub session_mapping: HashMap<i32, Vec<String>>,
}

impl Report {
    pub fn get_sessions_from_flags(&self, flags: &Vec<&str>) -> Vec<i32> {
        let mut res: Vec<i32> = Vec::new();
        for (session_id, session_flags) in self.session_mapping.iter() {
            if flags.iter().any(|v| session_flags.contains(&v.to_string())) {
                res.push(*session_id); // TODO Do I have to use this * ?
            }
        }
        return res;
    }

    pub fn get_by_filename(&self, filename: &str) -> Option<&file::ReportFile> {
        match self.filenames.get(filename) {
            Some(file_location) => match self.report_files.get(*file_location as usize) {
                None => {
                    return None;
                }
                Some(x) => {
                    return Some(x);
                }
            },
            None => {
                return None;
            }
        }
    }
}

#[pymethods]
impl Report {
    fn get_filtered_totals(&self, files: HashSet<&str>, flags: Vec<&str>) -> ReportTotals {
        let sessions = self.get_sessions_from_flags(&flags);
        let mut initial = ReportTotals::new();
        for filename in files {
            let location = self.filenames.get(filename);
            if let Some(i) = location {
                let report_file = &self.report_files[*i as usize];
                let some_totals = report_file.get_filtered_totals(&sessions);
                initial.add_up(&some_totals);
            }
        }
        return initial;
    }

    pub fn calculate_per_flag_totals(&self) -> HashMap<String, ReportTotals> {
        let mut book_reviews: HashMap<String, ReportTotals> = HashMap::new();
        for report_file in self.report_files.iter() {
            let file_totals = report_file.calculate_per_flag_totals(&self.session_mapping);
            for (flag_name, totals) in file_totals.iter() {
                let current = book_reviews
                    .entry(flag_name.to_string())
                    .or_insert(ReportTotals::new());
                current.add_up(&totals)
            }
        }
        return book_reviews;
    }

    pub fn get_totals(&self) -> PyResult<ReportTotals> {
        let mut res = ReportTotals::new();
        for report_file in self.report_files.iter() {
            let totals = report_file.get_totals();
            res.add_up(&totals);
        }
        return Ok(res);
    }
}

#[pymethods]
impl Report {
    pub fn get_eof(&self, file_number: i32) -> i32 {
        let file = &self.report_files[file_number as usize];
        file.get_eof()
    }
}
