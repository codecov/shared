use pyo3::prelude::*;
use std::collections::HashMap;
use std::collections::HashSet;

use crate::file;

#[pyclass]
#[derive(Debug)]
pub struct FileDiffAnalysis {
    #[pyo3(get)]
    pub summary: file::FileTotals,
    pub lines_with_misses: Vec<i32>,
    pub lines_with_partials: Vec<i32>,
    pub lines_with_hits: Vec<i32>,
}

type DiffSegment = ((i32, i32, i32, i32), Vec<String>);

pub type FileDiffData = (String, Option<String>, Vec<DiffSegment>);

pub type DiffInput = HashMap<String, FileDiffData>;

pub fn get_exclusions_from_diff(diff: Option<&Vec<DiffSegment>>) -> (HashSet<i32>, HashSet<i32>) {
    match diff {
        None => return (HashSet::new(), HashSet::new()),
        Some(val) => {
            let mut only_on_base: HashSet<i32> = HashSet::new();
            let mut only_on_head: HashSet<i32> = HashSet::new();
            for (headers, line_list) in val {
                let (start_base, _, start_head, _) = headers;
                let mut current_base: i32 = *start_base;
                let mut current_head: i32 = *start_head;
                for individual_line in line_list {
                    if individual_line == "+" {
                        only_on_head.insert(current_head);
                        current_head += 1;
                    } else if individual_line == "-" {
                        only_on_base.insert(current_base);
                        current_base += 1;
                    } else {
                        current_head += 1;
                        current_base += 1;
                    }
                }
            }
            return (only_on_base, only_on_head);
        }
    }
}
