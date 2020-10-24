use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use std::collections::HashMap;

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
    chunks: String,
    session_mapping: HashMap<i32, Vec<String>>,
) -> report::Report {
    parser::parse_report_from_str(filenames, chunks, session_mapping)
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustypole(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_report, m)?)?;
    m.add_class::<analyzers::filter::FilterAnalyzer>()?;
    m.add_class::<analyzers::simple::SimpleAnalyzer>()?;

    Ok(())
}
