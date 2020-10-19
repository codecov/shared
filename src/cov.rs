use pyo3::prelude::*;

use fraction::GenericFraction;
use fraction::ToPrimitive;

#[derive(PartialEq, Debug)]
pub enum Coverage {
    Hit,
    Miss,
    Partial(GenericFraction<i32>),
}

impl Coverage {
    pub fn get_value(&self) -> f64 {
        match self {
            Coverage::Hit => {
                return 1.0;
            }
            Coverage::Miss => {
                return 0.0;
            }
            Coverage::Partial(f) => {
                return f.to_f64().unwrap();
            }
        }
    }

    pub fn join_coverages(many_coverages: Vec<&Coverage>) -> Coverage {
        let mut a: Coverage = Coverage::Miss;
        for cov in many_coverages.iter() {
            match cov {
                Coverage::Hit => return Coverage::Hit,
                Coverage::Miss => {}
                Coverage::Partial(f) => {
                    if f.to_f64().unwrap() > a.get_value() {
                        a = Coverage::Partial(*f);
                    }
                }
            }
        }
        return a;
    }
}

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
        self.sessions += other.sessions;
        self.complexity += other.complexity;
        self.complexity_total += other.complexity_total;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn joining_coverage_works() {
        let v = Coverage::join_coverages(vec![
            &Coverage::Miss,
            &Coverage::Hit,
            &Coverage::Partial(GenericFraction::new(3, 10)),
        ]);
        assert_eq!(v, Coverage::Hit);
        let k = Coverage::join_coverages(vec![
            &Coverage::Miss,
            &Coverage::Partial(GenericFraction::new(3, 10)),
        ]);
        assert_eq!(k, Coverage::Partial(GenericFraction::new(3, 10)));
    }
}
