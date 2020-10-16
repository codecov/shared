use pyo3::prelude::*;

use fraction::GenericFraction;

#[pyclass]
pub struct ReportTotals {
    #[pyo3(get)]
    pub files: i32,
    pub lines: i32,
    #[pyo3(get)]
    pub hits: i32,
    pub misses: i32,
    pub partials: i32,
    pub branches: i32,
    pub methods: i32,
    pub sessions: i32,
    pub complexity: i32,
    pub complexity_total: i32,
}

#[pymethods]
impl ReportTotals {
    #[getter(coverage)]
    pub fn get_coverage(&self) -> PyResult<String> {
        if self.hits == self.lines {
            return Ok("100".to_string());
        }
        if self.hits == 0 || self.lines == 0 {
            return Ok("0".to_string());
        }
        let fraction: GenericFraction<i32> = GenericFraction::new(100 * self.hits, self.lines);
        Ok(format!("{:.1$}", fraction, 5))
    }

    pub fn add_up(&mut self, other: &ReportTotals) {
        self.files += other.files;
        self.lines += other.lines;
        self.hits += other.hits;
        self.misses += other.misses;
        self.partials += other.partials;
        self.branches += other.branches;
        self.methods += other.methods;
        self.sessions += other.sessions;
        self.complexity += other.complexity;
        self.complexity_total += other.complexity_total;
    }
}
