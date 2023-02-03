use std::collections::HashMap;
use std::collections::HashSet;
use std::iter::FromIterator;

use rayon::prelude::*;
use serde::Serialize;

use crate::cov;
use crate::diff;
use crate::file;
use crate::report;

type LineChange = ((i32, Option<cov::Coverage>), (i32, Option<cov::Coverage>));

#[derive(Debug, Serialize)]
pub struct FileChangesAnalysis {
    pub base_name: String,
    pub head_name: String,
    pub file_was_added_by_diff: bool,
    pub file_was_removed_by_diff: bool,
    pub base_coverage: Option<file::FileTotals>,
    pub head_coverage: Option<file::FileTotals>,
    pub removed_diff_coverage: Option<Vec<(i32, cov::Coverage)>>,
    pub added_diff_coverage: Option<Vec<(i32, cov::Coverage)>>,
    pub unexpected_line_changes: Vec<LineChange>,
    pub lines_only_on_base: Vec<i32>,
    pub lines_only_on_head: Vec<i32>,
}

#[derive(Debug, Serialize, PartialEq)]
pub struct ChangePatchTotals {
    hits: i32,
    misses: i32,
    partials: i32,
    coverage: Option<f32>,
}

#[derive(Debug, Serialize, PartialEq)]
pub struct ChangeAnalysisSummary {
    patch_totals: ChangePatchTotals,
}

#[derive(Serialize, Debug)]
pub struct ChangeAnalysis {
    pub files: Vec<FileChangesAnalysis>,
    changes_summary: ChangeAnalysisSummary,
}

pub fn run_comparison_analysis(
    base_report: &report::Report,
    head_report: &report::Report,
    diff: &diff::DiffInput,
) -> ChangeAnalysis {
    let possible_renames: HashMap<String, String> = diff
        .iter()
        .map(|(k, v)| (k, &v.1))
        .filter_map(|(k, v)| match v {
            None => None,
            Some(renamed) => Some((renamed.to_string(), k.to_string())),
        })
        .collect();
    let base_filenames_accounted_for_renames: HashSet<String> =
        HashSet::from_iter(base_report.report_files.keys().map(
            |f| match possible_renames.get(f) {
                None => f.to_string(),
                Some(v) => v.to_string(),
            },
        ));
    let head_filenames: HashSet<String> =
        HashSet::from_iter(head_report.report_files.keys().map(|f| f.clone()));
    let all_filenames: HashSet<String> = base_filenames_accounted_for_renames
        .union(&head_filenames)
        .map(|f| f.clone())
        .collect();
    let changes_list: Vec<FileChangesAnalysis> = all_filenames
        .iter()
        .map(|filename| {
            let diff_data = diff.get(filename);
            let original_name: String = match diff_data {
                Some(x) => match &x.1 {
                    None => filename.to_string(),
                    Some(o) => o.to_string(),
                },
                None => filename.to_string(),
            };
            if !base_report.get_by_filename(&original_name).is_none()
                || !head_report.get_by_filename(&filename).is_none()
            {
                run_filereport_analysis(
                    base_report.get_by_filename(&original_name),
                    head_report.get_by_filename(&filename),
                    diff_data,
                    (&original_name, &filename),
                )
            } else {
                None
            }
        })
        .filter_map(|x| x)
        .collect();
    return ChangeAnalysis {
        changes_summary: produce_summary_from_changes_list(&changes_list),
        files: changes_list,
    };
}

fn produce_summary_from_changes_list(
    changes_list: &Vec<FileChangesAnalysis>,
) -> ChangeAnalysisSummary {
    let mut patch_totals = ChangePatchTotals {
        hits: 0,
        misses: 0,
        partials: 0,
        coverage: None,
    };
    for fca in changes_list.iter() {
        match &fca.added_diff_coverage {
            None => {}
            Some(cov_vec) => {
                for (_, coverage) in cov_vec {
                    match coverage {
                        cov::Coverage::Hit => {
                            patch_totals.hits += 1;
                        }
                        cov::Coverage::Miss => {
                            patch_totals.misses += 1;
                        }
                        cov::Coverage::Partial(_) => {
                            patch_totals.partials += 1;
                        }
                        cov::Coverage::Ignore => {}
                    }
                }
            }
        }
    }
    let loc = patch_totals.hits + patch_totals.misses + patch_totals.partials;
    patch_totals.coverage = match loc {
        0 => None,
        _ => Some(patch_totals.hits as f32 / loc as f32),
    };
    ChangeAnalysisSummary {
        patch_totals: patch_totals,
    }
}

fn run_filereport_analysis(
    old_file: Option<&file::ReportFile>,
    new_file: Option<&file::ReportFile>,
    diff_data: Option<&diff::FileDiffData>,
    names_tuple: (&str, &str),
) -> Option<FileChangesAnalysis> {
    let (base_name, head_name) = names_tuple;
    let is_new = match diff_data {
        None => false,
        Some(value) => value.0 == "new",
    };
    let was_deleted = match diff_data {
        None => false,
        Some(value) => value.0 == "deleted",
    };
    let (only_on_base, only_on_head) = diff::get_exclusions_from_diff(match diff_data {
        None => None,
        Some(x) => Some(&x.2),
    });
    let removed_diff_coverage: Option<Vec<(i32, cov::Coverage)>> = match old_file {
        None => None,
        Some(file) => {
            let mut a: Vec<(i32, cov::Coverage)> = Vec::new();
            for line in &only_on_base {
                match file.lines.get(&line) {
                    None => {}
                    Some(l) => {
                        a.push((*line, l.coverage.to_owned()));
                    }
                }
            }
            a.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
            Some(a)
        }
    };
    let added_diff_coverage: Option<Vec<(i32, cov::Coverage)>> = match new_file {
        None => None,
        Some(file) => {
            let mut a: Vec<(i32, cov::Coverage)> = Vec::new();
            for line in &only_on_head {
                match file.lines.get(&line) {
                    None => {}
                    Some(l) => {
                        a.push((*line, l.coverage.to_owned()));
                    }
                }
            }
            a.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
            Some(a)
        }
    };
    let mut unexpected_vec = Vec::new();
    if !is_new && !was_deleted {
        let mut current_base: i32 = 0;
        let mut current_head: i32 = 0;
        let base_eof = match old_file {
            None => 0,
            Some(base_report) => base_report.get_eof(),
        };
        let head_eof = match new_file {
            None => 0,
            Some(head_report) => head_report.get_eof(),
        };
        while current_base < base_eof || current_head < head_eof {
            current_base += 1;
            current_head += 1;
            while only_on_base.contains(&current_base) {
                current_base += 1;
            }
            while only_on_head.contains(&current_head) {
                current_head += 1
            }
            match (
                match old_file {
                    None => None,
                    Some(base_report) => base_report.lines.get(&current_base),
                },
                match new_file {
                    None => None,
                    Some(head_report) => head_report.lines.get(&current_head),
                },
            ) {
                (None, None) => {}
                (None, Some(head_line)) => {
                    unexpected_vec.push((
                        (current_base, None),
                        (current_head, Some(head_line.coverage.to_owned())),
                    ));
                }
                (Some(base_line), None) => {
                    unexpected_vec.push((
                        (current_base, Some(base_line.coverage.to_owned())),
                        (current_head, None),
                    ));
                }
                (Some(base_line), Some(head_line)) => {
                    if base_line.coverage != head_line.coverage {
                        unexpected_vec.push((
                            (current_base, Some(base_line.coverage.to_owned())),
                            (current_head, Some(head_line.coverage.to_owned())),
                        ));
                    }
                }
            }
        }
    }
    let mut lines_only_on_head: Vec<_> = only_on_head.iter().map(|k| *k).collect();
    lines_only_on_head.sort();
    let mut lines_only_on_base: Vec<_> = only_on_base.iter().map(|k| *k).collect();
    lines_only_on_base.sort();
    return match (old_file, new_file) {
        (None, None) => None,
        (None, Some(new)) => Some(FileChangesAnalysis {
            file_was_added_by_diff: is_new,
            file_was_removed_by_diff: was_deleted,
            head_coverage: Some(new.get_totals()),
            base_coverage: None,
            removed_diff_coverage: removed_diff_coverage,
            added_diff_coverage: added_diff_coverage,
            unexpected_line_changes: unexpected_vec,
            base_name: base_name.to_string(),
            head_name: head_name.to_string(),
            lines_only_on_head: lines_only_on_head,
            lines_only_on_base: lines_only_on_base,
        }),
        (Some(old), None) => Some(FileChangesAnalysis {
            file_was_added_by_diff: is_new,
            file_was_removed_by_diff: was_deleted,
            head_coverage: None,
            base_coverage: Some(old.get_totals()),
            removed_diff_coverage: removed_diff_coverage,
            added_diff_coverage: added_diff_coverage,
            unexpected_line_changes: unexpected_vec,
            base_name: base_name.to_string(),
            head_name: head_name.to_string(),
            lines_only_on_head: lines_only_on_head,
            lines_only_on_base: lines_only_on_base,
        }),
        (Some(base_report), Some(head_report)) => {
            let has_removed_diff_coverage = match &removed_diff_coverage {
                None => false,
                Some(x) => !x.is_empty(),
            };
            let has_added_diff_coverage = match &added_diff_coverage {
                None => false,
                Some(x) => !x.is_empty(),
            };
            if unexpected_vec.is_empty()
                && !has_removed_diff_coverage
                && !has_added_diff_coverage
                && lines_only_on_base.is_empty()
                && lines_only_on_head.is_empty()
            {
                return None;
            }
            return Some(FileChangesAnalysis {
                added_diff_coverage: added_diff_coverage,
                base_coverage: Some(base_report.get_totals()),
                base_name: base_name.to_string(),
                file_was_added_by_diff: is_new,
                file_was_removed_by_diff: was_deleted,
                head_coverage: Some(head_report.get_totals()),
                head_name: head_name.to_string(),
                removed_diff_coverage: removed_diff_coverage,
                unexpected_line_changes: unexpected_vec,
                lines_only_on_head: lines_only_on_head,
                lines_only_on_base: lines_only_on_base,
            });
        }
    };
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::line;
    use fraction::GenericFraction;

    fn create_line_for_test(line_number: i32, coverage: cov::Coverage) -> (i32, line::ReportLine) {
        (
            line_number,
            line::ReportLine {
                coverage: coverage.clone(),
                coverage_type: line::CoverageType::Standard,
                sessions: vec![line::LineSession {
                    id: 0,
                    coverage: coverage,
                    complexity: None,
                }],
                complexity: None,
            },
        )
    }

    #[test]
    fn get_changes_works() {
        let first_report = report::Report {
            report_files: vec![
                (
                    "apple".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(1, cov::Coverage::Hit),
                            (
                                2,
                                line::ReportLine {
                                    coverage: cov::Coverage::Hit,
                                    coverage_type: line::CoverageType::Standard,
                                    sessions: vec![
                                        line::LineSession {
                                            id: 0,
                                            coverage: cov::Coverage::Hit,
                                            complexity: None,
                                        },
                                        line::LineSession {
                                            id: 1,
                                            coverage: cov::Coverage::Partial(GenericFraction::new(
                                                1, 2,
                                            )),
                                            complexity: None,
                                        },
                                    ],
                                    complexity: None,
                                },
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "another_unmodified.py".to_string(),
                    file::ReportFile {
                        lines: vec![(
                            22,
                            line::ReportLine {
                                coverage: cov::Coverage::Hit,
                                coverage_type: line::CoverageType::Standard,
                                sessions: vec![line::LineSession {
                                    id: 0,
                                    coverage: cov::Coverage::Hit,
                                    complexity: None,
                                }],
                                complexity: None,
                            },
                        )]
                        .into_iter()
                        .collect(),
                    },
                ),
            ]
            .into_iter()
            .collect(),
            session_mapping: vec![
                (0, vec!["unit".to_string()]),
                (1, vec!["integration".to_string()]),
            ]
            .into_iter()
            .collect(),
        };
        let second_report = report::Report {
            report_files: vec![
                (
                    "file1.go".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(1, cov::Coverage::Hit),
                            (
                                2,
                                line::ReportLine {
                                    coverage: cov::Coverage::Miss,
                                    coverage_type: line::CoverageType::Standard,
                                    sessions: vec![line::LineSession {
                                        id: 1,
                                        coverage: cov::Coverage::Miss,
                                        complexity: None,
                                    }],
                                    complexity: None,
                                },
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_p.py".to_string(),
                    file::ReportFile {
                        lines: vec![].into_iter().collect(),
                    },
                ),
                (
                    "another_unmodified.py".to_string(),
                    file::ReportFile {
                        lines: vec![(
                            22,
                            line::ReportLine {
                                coverage: cov::Coverage::Hit,
                                coverage_type: line::CoverageType::Standard,
                                sessions: vec![line::LineSession {
                                    id: 0,
                                    coverage: cov::Coverage::Hit,
                                    complexity: None,
                                }],
                                complexity: None,
                            },
                        )]
                        .into_iter()
                        .collect(),
                    },
                ),
            ]
            .into_iter()
            .collect(),
            session_mapping: vec![
                (0, vec!["unit".to_string()]),
                (1, vec!["integration".to_string()]),
            ]
            .into_iter()
            .collect(),
        };
        let diff: diff::DiffInput = vec![
            (
                ("file1.go").to_string(),
                (
                    "changed".to_string(),
                    Some("apple".to_string()),
                    vec![((1, 0, 1, 1), vec!["+".to_string()])],
                ),
            ),
            (
                ("file_p.py").to_string(),
                (
                    "new".to_string(),
                    None,
                    vec![((1, 0, 1, 1), vec!["+".to_string()])],
                ),
            ),
        ]
        .into_iter()
        .collect();
        let res = run_comparison_analysis(&first_report, &second_report, &diff);
        let mut files_array: Vec<_> = res.files;
        let present_keys: HashSet<String> =
            files_array.iter().map(|f| f.head_name.to_owned()).collect();
        assert!(present_keys.contains(&"file_p.py".to_string()));
        assert!(present_keys.contains(&"file1.go".to_string()));
        assert_eq!(present_keys.len(), 2);
        files_array.sort_by(|a, b| a.base_name.partial_cmp(&b.base_name).unwrap());
        let one_case = files_array.get(0).unwrap();
        assert_eq!(one_case.base_name, "apple");
        assert_eq!(one_case.file_was_added_by_diff, false);
        assert_eq!(one_case.file_was_removed_by_diff, false);
        assert_eq!(
            one_case.added_diff_coverage,
            Some(vec![(1, cov::Coverage::Hit)])
        );
        assert_eq!(one_case.removed_diff_coverage, Some(vec![]));
        assert_eq!(one_case.unexpected_line_changes.len(), 2);
    }

    #[test]
    fn last_line_near_end_case() {
        let diff: diff::DiffInput = vec![(
            "file1.go".to_string(),
            (
                "modified".to_string(),
                None,
                vec![(
                    (988, 15, 988, 16),
                    vec![
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        "-".to_string(),
                        "-".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        "+".to_string(),
                        "+".to_string(),
                        "+".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                        " ".to_string(),
                    ],
                )],
            ),
        )]
        .into_iter()
        .collect();
        let first_report = report::Report {
            report_files: vec![(
                "file1.go".to_string(),
                file::ReportFile {
                    lines: vec![
                        create_line_for_test(1079, cov::Coverage::Hit),
                        create_line_for_test(1075, cov::Coverage::Miss),
                    ]
                    .into_iter()
                    .collect(),
                },
            )]
            .into_iter()
            .collect(),
            session_mapping: vec![(0, vec!["unit".to_string()])].into_iter().collect(),
        };
        let second_report = report::Report {
            report_files: vec![(
                "file1.go".to_string(),
                file::ReportFile {
                    lines: vec![create_line_for_test(1076, cov::Coverage::Miss)]
                        .into_iter()
                        .collect(),
                },
            )]
            .into_iter()
            .collect(),
            session_mapping: vec![(0, vec!["unit".to_string()])].into_iter().collect(),
        };
        let full_res = run_comparison_analysis(&first_report, &second_report, &diff);
        println!("{:?}", full_res);
        assert_eq!(
            full_res.changes_summary,
            ChangeAnalysisSummary {
                patch_totals: ChangePatchTotals {
                    hits: 0,
                    misses: 0,
                    partials: 0,
                    coverage: None
                }
            }
        );
        assert_eq!(full_res.files.len(), 1);
        let first_result_file = &full_res.files[0];
        assert_eq!(first_result_file.base_name, "file1.go");
        assert_eq!(first_result_file.head_name, "file1.go");
        assert_eq!(first_result_file.file_was_added_by_diff, false);
        assert_eq!(first_result_file.file_was_removed_by_diff, false);
        assert_eq!(
            first_result_file.base_coverage,
            Some(file::FileTotals {
                hits: 1,
                misses: 1,
                partials: 0,
                branches: 0,
                sessions: 0,
                complexity: 0,
                complexity_total: 0,
                methods: 0
            })
        );
        assert_eq!(
            first_result_file.head_coverage,
            Some(file::FileTotals {
                hits: 0,
                misses: 1,
                partials: 0,
                branches: 0,
                sessions: 0,
                complexity: 0,
                complexity_total: 0,
                methods: 0
            })
        );
        assert_eq!(first_result_file.removed_diff_coverage, Some(vec![]));
        assert_eq!(first_result_file.added_diff_coverage, Some(vec![]));
        assert_eq!(
            first_result_file.unexpected_line_changes,
            [((1079, Some(cov::Coverage::Hit)), (1080, None))]
        );
        assert_eq!(first_result_file.lines_only_on_base, [991, 992]);
        assert_eq!(first_result_file.lines_only_on_head, [998, 999, 1000]);
        assert_eq!(
            full_res.changes_summary,
            ChangeAnalysisSummary {
                patch_totals: ChangePatchTotals {
                    hits: 0,
                    misses: 0,
                    partials: 0,
                    coverage: None
                }
            }
        );
    }

    #[test]
    fn complete_case() {
        let diff: diff::DiffInput = vec![
            (
                ("file_with_diff_only.md").to_string(),
                (
                    "changed".to_string(),
                    None,
                    vec![((1, 0, 1, 1), vec!["+".to_string()])],
                ),
            ),
            (
                ("renamed_new.c").to_string(),
                (
                    "changed".to_string(),
                    Some("renamed_old.c".to_string()),
                    vec![((1, 0, 1, 1), vec!["+".to_string()])],
                ),
            ),
            (
                ("renamed_new_with_changes.c").to_string(),
                (
                    "changed".to_string(),
                    Some("renamed_old_with_changes.c".to_string()),
                    vec![((100, 1, 100, 1), vec!["-".to_string(), "+".to_string()])],
                ),
            ),
            (
                ("removed_file.c").to_string(),
                (
                    "deleted".to_string(),
                    None,
                    vec![(
                        (1, 4, 1, 0),
                        vec![
                            "-".to_string(),
                            "-".to_string(),
                            "-".to_string(),
                            "-".to_string(),
                        ],
                    )],
                ),
            ),
            (
                ("added_file.c").to_string(),
                (
                    "new".to_string(),
                    None,
                    vec![((1, 0, 1, 10), vec!["+".to_string(); 10])],
                ),
            ),
            (
                ("file_with_unexpected_changes.c").to_string(),
                (
                    "changed".to_string(),
                    None,
                    vec![(
                        (21, 3, 21, 2),
                        vec![
                            "-".to_string(),
                            "-".to_string(),
                            "-".to_string(),
                            "+".to_string(),
                            "+".to_string(),
                        ],
                    )],
                ),
            ),
            (
                ("file_with_unexpec_and_cov_diff.c").to_string(),
                (
                    "changed".to_string(),
                    None,
                    vec![(
                        (65, 5, 65, 4),
                        vec![
                            "-".to_string(),
                            "-".to_string(),
                            "-".to_string(),
                            "-".to_string(),
                            "-".to_string(),
                            "+".to_string(),
                            "+".to_string(),
                            "+".to_string(),
                            "+".to_string(),
                        ],
                    )],
                ),
            ),
            (
                ("file_with_cov_remov_and_add.c").to_string(),
                (
                    "changed".to_string(),
                    None,
                    vec![
                        (
                            (5, 2, 5, 3),
                            vec![
                                "-".to_string(),
                                "-".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                            ],
                        ),
                        (
                            (15, 3, 16, 10),
                            vec![
                                "-".to_string(),
                                "-".to_string(),
                                " ".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                                "+".to_string(),
                            ],
                        ),
                    ],
                ),
            ),
        ]
        .into_iter()
        .collect();

        let first_report = report::Report {
            report_files: vec![
                (
                    "unrelated_file.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(76, cov::Coverage::Hit),
                            create_line_for_test(79, cov::Coverage::Hit),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_with_cov_remov_and_add.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(6, cov::Coverage::Hit),
                            create_line_for_test(8, cov::Coverage::Hit),
                            create_line_for_test(16, cov::Coverage::Hit),
                            create_line_for_test(17, cov::Coverage::Hit),
                            create_line_for_test(
                                18,
                                cov::Coverage::Partial(GenericFraction::new(1, 2)),
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_with_unexpected_changes.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(5, cov::Coverage::Hit),
                            create_line_for_test(10, cov::Coverage::Miss),
                            create_line_for_test(15, cov::Coverage::Hit),
                            create_line_for_test(20, cov::Coverage::Hit),
                            create_line_for_test(
                                25,
                                cov::Coverage::Partial(GenericFraction::new(1, 4)),
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_with_unexpec_and_cov_diff.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(64, cov::Coverage::Hit),
                            create_line_for_test(65, cov::Coverage::Hit),
                            create_line_for_test(66, cov::Coverage::Hit),
                            create_line_for_test(67, cov::Coverage::Miss),
                            create_line_for_test(68, cov::Coverage::Hit),
                            create_line_for_test(69, cov::Coverage::Hit),
                            create_line_for_test(70, cov::Coverage::Hit),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "removed_file.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(1, cov::Coverage::Hit),
                            create_line_for_test(2, cov::Coverage::Miss),
                            create_line_for_test(3, cov::Coverage::Ignore),
                            create_line_for_test(
                                4,
                                cov::Coverage::Partial(GenericFraction::new(1, 3)),
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "renamed_old.c".to_string(),
                    file::ReportFile {
                        lines: vec![create_line_for_test(
                            101,
                            cov::Coverage::Partial(GenericFraction::new(1, 2)),
                        )]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "renamed_old_with_changes.c".to_string(),
                    file::ReportFile {
                        lines: vec![create_line_for_test(
                            101,
                            cov::Coverage::Partial(GenericFraction::new(1, 2)),
                        )]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "missing.c".to_string(),
                    file::ReportFile {
                        lines: vec![create_line_for_test(2, cov::Coverage::Miss)]
                            .into_iter()
                            .collect(),
                    },
                ),
            ]
            .into_iter()
            .collect(),
            session_mapping: vec![].into_iter().collect(),
        };

        let second_report = report::Report {
            report_files: vec![
                (
                    "unrelated_file.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(76, cov::Coverage::Hit),
                            create_line_for_test(79, cov::Coverage::Hit),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_with_cov_remov_and_add.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(6, cov::Coverage::Hit),
                            create_line_for_test(9, cov::Coverage::Hit),
                            create_line_for_test(16, cov::Coverage::Hit),
                            create_line_for_test(17, cov::Coverage::Hit),
                            create_line_for_test(
                                26,
                                cov::Coverage::Partial(GenericFraction::new(1, 2)),
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_with_unexpected_changes.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(5, cov::Coverage::Hit),
                            create_line_for_test(10, cov::Coverage::Miss),
                            create_line_for_test(15, cov::Coverage::Miss),
                            create_line_for_test(20, cov::Coverage::Hit),
                            create_line_for_test(
                                25,
                                cov::Coverage::Partial(GenericFraction::new(1, 4)),
                            ),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "file_with_unexpec_and_cov_diff.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(
                                64,
                                cov::Coverage::Partial(GenericFraction::new(1, 4)),
                            ),
                            create_line_for_test(65, cov::Coverage::Hit),
                            create_line_for_test(66, cov::Coverage::Hit),
                            create_line_for_test(67, cov::Coverage::Miss),
                            create_line_for_test(68, cov::Coverage::Hit),
                            create_line_for_test(69, cov::Coverage::Ignore),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "added_file.c".to_string(),
                    file::ReportFile {
                        lines: vec![
                            create_line_for_test(1, cov::Coverage::Miss),
                            create_line_for_test(4, cov::Coverage::Miss),
                        ]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "renamed_new.c".to_string(),
                    file::ReportFile {
                        lines: vec![create_line_for_test(
                            102,
                            cov::Coverage::Partial(GenericFraction::new(1, 2)),
                        )]
                        .into_iter()
                        .collect(),
                    },
                ),
                (
                    "renamed_new_with_changes.c".to_string(),
                    file::ReportFile {
                        lines: vec![create_line_for_test(
                            102,
                            cov::Coverage::Partial(GenericFraction::new(1, 2)),
                        )]
                        .into_iter()
                        .collect(),
                    },
                ),
            ]
            .into_iter()
            .collect(),
            session_mapping: vec![].into_iter().collect(),
        };
        let full_res = run_comparison_analysis(&first_report, &second_report, &diff);
        println!("{}", serde_json::to_string(&full_res).unwrap());
        assert_eq!(
            full_res.changes_summary,
            ChangeAnalysisSummary {
                patch_totals: ChangePatchTotals {
                    hits: 5,
                    misses: 3,
                    partials: 0,
                    coverage: Some(0.625)
                }
            }
        );
        let mut res = full_res.files;
        // Sorting now will allow the below assertions to be deterministic
        res.sort_by(|a, b| a.base_name.partial_cmp(&b.base_name).unwrap());
        assert_eq!(
            vec![
                "added_file.c",
                "file_with_cov_remov_and_add.c",
                "file_with_unexpec_and_cov_diff.c",
                "file_with_unexpected_changes.c",
                "missing.c",
                "removed_file.c",
                "renamed_new.c",
                "renamed_new_with_changes.c",
            ],
            res.iter()
                .map(|b| b.head_name.to_string())
                .into_iter()
                .collect::<Vec<_>>()
        );
        assert_eq!(
            vec![
                "added_file.c",
                "file_with_cov_remov_and_add.c",
                "file_with_unexpec_and_cov_diff.c",
                "file_with_unexpected_changes.c",
                "missing.c",
                "removed_file.c",
                "renamed_old.c",
                "renamed_old_with_changes.c"
            ],
            res.iter()
                .map(|b| b.base_name.to_string())
                .into_iter()
                .collect::<Vec<_>>()
        );
        assert_eq!(
            vec![true, false, false, false, false, false, false, false],
            res.iter()
                .map(|b| b.file_was_added_by_diff)
                .into_iter()
                .collect::<Vec<_>>()
        );
        assert_eq!(
            vec![false, false, false, false, false, true, false, false],
            res.iter()
                .map(|b| b.file_was_removed_by_diff)
                .into_iter()
                .collect::<Vec<_>>()
        );
        let results_mapping: HashMap<String, _> = res
            .into_iter()
            .map(|a| (a.base_name.to_string(), a))
            .collect();
        let file_with_unexpec_and_cov_diff = results_mapping
            .get("file_with_unexpec_and_cov_diff.c")
            .expect("There should be a file_with_unexpec_and_cov_diff file here");
        assert_eq!(
            file_with_unexpec_and_cov_diff.unexpected_line_changes,
            vec![
                (
                    (64, Some(cov::Coverage::Hit)),
                    (64, Some(cov::Coverage::Partial(GenericFraction::new(1, 4))))
                ),
                (
                    (70, Some(cov::Coverage::Hit)),
                    (69, Some(cov::Coverage::Ignore))
                )
            ]
        );
        assert_eq!(
            file_with_unexpec_and_cov_diff.removed_diff_coverage,
            Some(vec![
                (65, cov::Coverage::Hit),
                (66, cov::Coverage::Hit),
                (67, cov::Coverage::Miss),
                (68, cov::Coverage::Hit),
                (69, cov::Coverage::Hit),
            ])
        );
        assert_eq!(
            file_with_unexpec_and_cov_diff.added_diff_coverage,
            Some(vec![
                (65, cov::Coverage::Hit),
                (66, cov::Coverage::Hit),
                (67, cov::Coverage::Miss),
                (68, cov::Coverage::Hit),
            ])
        );
    }
}
