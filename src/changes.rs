use pyo3::prelude::*;
use std::collections::HashMap;
use std::collections::HashSet;
use std::iter::FromIterator;

use crate::cov;
use crate::diff;
use crate::report;

struct ChangeStats {
    hits: i32,
    partials: i32,
    misses: i32,
}

#[pyclass]
pub struct Change {
    path: String,
    is_new: bool,
    was_deleted: bool,
    in_diff: bool,
    old_path: Option<String>,
    totals: Option<ChangeStats>,
}

fn get_filereport_changes(
    base_report: &report::ReportFile,
    head_report: &report::ReportFile,
    filename: &str,
    original_name: &str,
    diff: Option<&(
        String,
        Option<String>,
        Vec<((i32, i32, i32, i32), Vec<String>)>,
    )>,
) -> Option<Change> {
    let (only_on_base, only_on_head) = diff::get_exclusions_from_diff(match diff {
        None => None,
        Some(x) => Some(&x.2),
    });
    let mut head_coverages: Vec<&cov::Coverage> = Vec::new();
    let mut base_coverages: Vec<&cov::Coverage> = Vec::new();
    let mut current_base: i32 = 0;
    let mut current_head: i32 = 0;
    let base_eof = base_report.get_eof();
    let head_eof = head_report.get_eof();
    while current_base < base_eof && current_head < head_eof {
        current_base += 1;
        current_head += 1;
        while only_on_base.contains(&current_base) {
            current_base += 1;
        }
        while only_on_head.contains(&current_head) {
            current_head += 1
        }
        match base_report.lines.get(&current_base) {
            Some(base_line) => match head_report.lines.get(&current_head) {
                None => {
                    base_coverages.push(&base_line.coverage);
                }
                Some(head_line) => {
                    if head_line.coverage != base_line.coverage {
                        head_coverages.push(&head_line.coverage);
                        base_coverages.push(&base_line.coverage);
                    }
                }
            },
            None => match head_report.lines.get(&current_head) {
                None => {}
                Some(head_line) => {
                    head_coverages.push(&head_line.coverage);
                }
            },
        }
    }
    if head_coverages.is_empty() && base_coverages.is_empty() {
        return None;
    }
    let (head_hits, head_misses, head_partials) =
        head_coverages
            .iter()
            .fold((0, 0, 0), |(hits, misses, partials), x| match x {
                cov::Coverage::Hit => (hits + 1, misses, partials),
                cov::Coverage::Miss => (hits, misses + 1, partials),
                cov::Coverage::Partial(_) => (hits, misses, partials + 1),
            });

    let (base_hits, base_misses, base_partials) =
        base_coverages
            .iter()
            .fold((0, 0, 0), |(hits, misses, partials), x| match x {
                cov::Coverage::Hit => (hits + 1, misses, partials),
                cov::Coverage::Miss => (hits, misses + 1, partials),
                cov::Coverage::Partial(_) => (hits, misses, partials + 1),
            });
    let hits = head_hits - base_hits;
    let misses = head_misses - base_misses;
    let partials = head_partials - base_partials;
    Some(Change {
        path: filename.to_string(),
        is_new: false,
        was_deleted: false,
        in_diff: diff.is_some(),
        old_path: if original_name == filename {
            None
        } else {
            Some(original_name.to_string())
        },
        totals: Some(ChangeStats {
            hits,
            misses,
            partials,
        }),
    })
}

#[pyfunction]
pub fn get_changes(
    base_report: &report::Report,
    head_report: &report::Report,
    diff: HashMap<
        String,
        (
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
    >,
) -> Vec<Change> {
    let mut changes_list = Vec::new();
    let base_filenames: HashSet<String> =
        HashSet::from_iter(base_report.filenames.keys().map(|f| f.clone()));
    let head_filenames: HashSet<String> =
        HashSet::from_iter(head_report.filenames.keys().map(|f| f.clone()));
    let files_in_diff: HashSet<String> = HashSet::from_iter(diff.keys().map(|f| f.clone()));
    let files_that_were_moved: HashSet<String> = HashSet::from_iter(
        diff.values()
            .filter_map(|(_, b, _)| b.as_ref())
            .map(|f| f.clone()),
    );
    let files_that_went_somewhere: HashSet<_> =
        files_in_diff.union(&files_that_were_moved).collect();
    let originally_missing_files: HashSet<_> = base_filenames.difference(&head_filenames).collect();
    let originally_new_filenames: HashSet<_> = head_filenames.difference(&base_filenames).collect();
    let missing_files: HashSet<_> = originally_missing_files
        .difference(&files_that_went_somewhere)
        .collect();
    let new_filenames: HashSet<_> = originally_new_filenames
        .difference(&files_that_went_somewhere)
        .collect();
    for (filename, file_location) in head_report.filenames.iter() {
        let diff_data = diff.get(filename);
        if !(&new_filenames.contains(&filename)) {
            let original_name: String = match diff_data {
                Some(x) => match &x.1 {
                    None => filename.to_string(),
                    Some(o) => o.to_string(),
                },
                None => filename.to_string(),
            };
            let new_file: &report::ReportFile = head_report
                .report_files
                .get(*file_location as usize)
                .unwrap();
            let old_file_location = base_report.filenames.get(&original_name).unwrap();
            let old_file: &report::ReportFile = base_report
                .report_files
                .get(*old_file_location as usize)
                .unwrap();
            match get_filereport_changes(old_file, new_file, filename, &original_name, diff_data) {
                Some(x) => {
                    changes_list.push(x);
                }
                None => {}
            }
        }
    }
    for filename in missing_files {
        changes_list.push(Change {
            path: filename.to_string(),
            was_deleted: true,
            is_new: false,
            in_diff: false,
            old_path: None,
            totals: None,
        })
    }

    for filename in new_filenames {
        changes_list.push(Change {
            path: filename.to_string(),
            is_new: true,
            was_deleted: false,
            in_diff: false,
            old_path: None,
            totals: None,
        })
    }
    return changes_list;
}
