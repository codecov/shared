use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use std::collections::HashMap;
use std::collections::HashSet;

mod changes;
mod cov;
mod diff;
mod line;
mod parser;
mod report;
mod file;

#[pyfunction]
fn parse_report(
    filenames: HashMap<String, i32>,
    chunks: String,
    session_mapping: HashMap<i32, Vec<String>>,
) -> report::Report {
    parser::parse_report_from_str(filenames, chunks, session_mapping)
}

#[pyfunction]
fn get_changes(
    old_report: &report::Report,
    new_report: &report::Report,
    diff: HashMap<
        String,
        (
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
    >,
) -> Vec<changes::Change> {
    changes::get_changes(old_report, new_report, diff)
}

#[pyfunction]
fn calculate_diff(
    report: &report::Report,
    diff: HashMap<
        String,
        (
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
    >,
) -> (report::ReportTotals, HashMap<String, file::FileTotals>) {
    return diff::calculate_diff(report, diff);
}

#[pyfunction]
fn calculate_filtered_diff(
    report: &report::Report,
    diff: HashMap<
        String,
        (
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
    >,
    files: HashSet<String>,
    flags: Vec<&str>,
) -> (report::ReportTotals, HashMap<String, file::FileTotals>) {
    return diff::calculate_filtered_diff(report, diff, files, flags);
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustypole(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_report, m)?)?;
    m.add_function(wrap_pyfunction!(get_changes, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_diff, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_filtered_diff, m)?)?;

    Ok(())
}
