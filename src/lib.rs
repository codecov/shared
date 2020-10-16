use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use std::collections::HashMap;

mod changes;
mod cov;
mod report;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn parse_report(
    filenames: HashMap<String, i32>,
    chunks: String,
    session_mapping: HashMap<i32, Vec<String>>,
) -> report::Report {
    report::parse_report_from_str(filenames, chunks, session_mapping)
}

#[pyfunction]
fn get_changes(
    old_report: &report::Report,
    new_report: &report::Report,
    diff: HashMap<String, (String, Option<String>, Vec<((i32, i32, i32, i32), Vec<String>)>)>,
) -> Vec<changes::Change> {
    changes::get_changes(old_report, new_report, diff)
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustypole(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(parse_report, m)?)?;
    m.add_function(wrap_pyfunction!(get_changes, m)?)?;

    Ok(())
}
