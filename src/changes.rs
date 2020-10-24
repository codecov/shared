use fraction::GenericFraction;
use pyo3::prelude::*;

#[pyclass]
#[derive(Clone, Debug)]
pub struct ChangeStats {
    #[pyo3(get)]
    pub hits: i32,
    #[pyo3(get)]
    pub partials: i32,
    #[pyo3(get)]
    pub misses: i32,
    pub changed_coverage: GenericFraction<i32>,
}

#[pymethods]
impl ChangeStats {
    #[getter(coverage)]
    pub fn get_coverage(&self) -> PyResult<Option<String>> {
        Ok(Some(format!("{:.1$}", self.changed_coverage, 5)))
    }
}

#[pyclass]
#[derive(Debug)]
pub struct Change {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub new: bool,
    #[pyo3(get)]
    pub deleted: bool,
    pub in_diff: bool,
    pub old_path: Option<String>,
    #[pyo3(get)]
    pub totals: Option<ChangeStats>,
}
