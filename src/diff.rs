use std::collections::HashMap;
use std::collections::HashSet;

use crate::report;

fn calculate_reportfile_diff(
    reportfile: &report::ReportFile,
    diff_data: &(
        String,
        Option<String>,
        Vec<((i32, i32, i32, i32), Vec<String>)>,
    ),
) -> report::ReportTotals {
    let (_, lines_on_head) = get_exclusions_from_diff(Some(&diff_data.2));
    let mut involved_lines: Vec<&report::ReportLine> = Vec::new();
    println!("{:?}", lines_on_head);
    for line_number in lines_on_head.iter() {
        match reportfile.lines.get(line_number) {
            None => {}
            Some(line) => involved_lines.push(line),
        }
    }
    return report::ReportTotals::from_lines(involved_lines);
}

pub fn calculate_diff(
    report: &report::Report,
    diff: HashMap<
        String,
        (
            String,
            Option<String>,
            Vec<((i32, i32, i32, i32), Vec<String>)>,
        ),
    >,
) -> (report::ReportTotals, HashMap<String, report::ReportTotals>) {
    let mut res = report::ReportTotals::new();
    let mut mapping: HashMap<String, report::ReportTotals> = HashMap::new();
    for (filename, diff_data) in diff.iter() {
        match report.get_by_filename(filename) {
            None => {}
            Some(file_report) => {
                let file_res = calculate_reportfile_diff(file_report, diff_data);
                res.add_up(&file_res);
                mapping.insert(filename.to_string(), file_res);
            }
        }
    }
    return (res, mapping);
}

pub fn get_exclusions_from_diff(
    diff: Option<&Vec<((i32, i32, i32, i32), Vec<String>)>>,
) -> (HashSet<i32>, HashSet<i32>) {
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
