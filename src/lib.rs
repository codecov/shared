use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use std::collections::HashMap;

mod report;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

/// Formats the sum of two numbers as string.
#[pyfunction]
fn parse_report(filenames: HashMap<String, i32>, chunks: String, session_mapping: HashMap<i32, Vec<String>>) -> report::Report {
    let r = report::parse_report_from_str(filenames, chunks, session_mapping);
    return r;
    // I thought this function should return Py<report::Report>, but this works and I dont know if this is right
    // If this was necessary, the below code would be needed.
    // We will figure this out
    // let gil = Python::acquire_gil();
    // let py = gil.python();
    // Py::new(py, r).unwrap()
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustypole(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(parse_report, m)?)?;

    Ok(())
}
