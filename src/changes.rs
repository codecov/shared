use pyo3::prelude::*;
use std::collections::HashMap;

use crate::cov;
use crate::report;

#[pyclass]
pub struct Change {
    path: String,
    new: bool,
    deleted: bool,
    in_diff: bool,
    old_path: String,
    totals: cov::ReportTotals,
}

#[pyfunction]
pub fn get_changes(
    old_report: &report::Report,
    new_report: &report::Report,
    diff: HashMap<String, (String, Option<String>, Vec<((i32, i32, i32, i32), Vec<String>)>)>,
) -> Vec<Change> {
    let new = Vec::new();
    return new;
}
