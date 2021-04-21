use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::collections::HashMap;

#[cfg(target_env = "musl")]
#[global_allocator]
static ALLOC: jemallocator::Jemalloc = jemallocator::Jemalloc;

mod analyzers;
mod changes;
mod cov;
mod diff;
mod file;
mod line;
mod parser;
mod report;

#[pyfunction]
fn parse_report(
    filenames: HashMap<String, i32>,
    chunks: &str,
    session_mapping: HashMap<i32, Vec<String>>,
) -> PyResult<report::Report> {
    let res = parser::parse_report_from_str(filenames, chunks, session_mapping);
    match res {
        Ok(val) => return Ok(val),
        Err(_) => return Err(PyException::new_err("Unable to parse rust report")),
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustypole(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_report, m)?)?;
    m.add_class::<analyzers::filter::FilterAnalyzer>()?;
    m.add_class::<analyzers::simple::SimpleAnalyzer>()?;

    Ok(())
}
