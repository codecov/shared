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
mod profiling;
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

#[pyfunction]
fn run_comparison_as_json(
    base_report: &report::Report,
    head_report: &report::Report,
    diff: diff::DiffInput,
) -> PyResult<String> {
    return match serde_json::to_string(&changes::run_comparison_analysis(
        base_report,
        head_report,
        &diff,
    )) {
        Ok(value) => Ok(value),
        Err(_) => Err(PyException::new_err("Error serializing changes")),
    };
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustyribs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_report, m)?)?;
    m.add_function(wrap_pyfunction!(run_comparison_as_json, m)?)?;
    m.add_class::<analyzers::filter::FilterAnalyzer>()?;
    m.add_class::<analyzers::simple::SimpleAnalyzer>()?;
    m.add_class::<profiling::ProfilingData>()?;

    Ok(())
}
