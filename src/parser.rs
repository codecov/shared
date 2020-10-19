extern crate rayon;
use crate::cov;
use crate::report;

use fraction::GenericFraction;
use fraction::ToPrimitive;
use pyo3::prelude::*;
use rayon::prelude::*;

use serde_json::Value;
use std::collections::HashMap;

enum LineType {
    Content(report::ReportLine),
    Emptyline,
    Separator,
    Details,
}

fn parse_coverage(line: &Value) -> cov::Coverage {
    match line {
        Value::Number(o) => {
            return if o.as_i64().unwrap() > 0 {
                cov::Coverage::Hit
            } else {
                cov::Coverage::Miss
            }
        }
        Value::String(s) => match s.rfind("/") {
            Some(_) => {
                let v: Vec<&str> = s.rsplit('/').collect();
                let num: i32 = v[0].parse().unwrap();
                let den: i32 = v[1].parse().unwrap();
                let f: GenericFraction<i32> = GenericFraction::new(num, den);
                return cov::Coverage::Partial(f);
            }
            None => {
                let val: i32 = s.parse().unwrap();
                return if val > 0 {
                    cov::Coverage::Hit
                } else {
                    cov::Coverage::Miss
                };
            }
        },
        Value::Array(a) => panic!("Array {:?}", a),
        Value::Null => return cov::Coverage::Miss,
        Value::Bool(_) => panic!("BOOL"),
        Value::Object(_) => panic!("Object"),
    }
}

fn parse_line(line: &str) -> LineType {
    if line.is_empty() {
        return LineType::Emptyline;
    }
    if line == "<<<<< end_of_chunk >>>>>" {
        return LineType::Separator;
    }
    match serde_json::from_str(&line).unwrap() {
        Value::Number(o) => panic!("{:?}", o),
        Value::String(s) => panic!("{:?}", s),
        Value::Array(array_data) => {
            let mut sessions: Vec<report::LineSession> = Vec::new();
            for el in array_data[2].as_array().unwrap() {
                sessions.push(report::LineSession {
                    id: el[0].as_i64().unwrap() as i32,
                    coverage: parse_coverage(&el[1]),
                    branches: 0,
                    partials: [0].to_vec(),
                    complexity: 0,
                })
            }
            return LineType::Content(report::ReportLine {
                coverage: parse_coverage(&array_data[0]),
                coverage_type: report::CoverageType::Standard, // TODO: fix this
                sessions: sessions,
                complexity: Option::None,
            });
        }
        Value::Null => return LineType::Emptyline,
        Value::Bool(_) => panic!("{:?}", "BOOL"),
        Value::Object(_) => return LineType::Details,
    }
}

pub fn parse_report_from_str(
    filenames: HashMap<String, i32>,
    chunks: String,
    session_mapping: HashMap<i32, Vec<String>>,
) -> report::Report {
    let v: Vec<_> = chunks.par_lines().map(|line| parse_line(&line)).collect();
    let mut current_report_lines: HashMap<i32, report::ReportLine> = HashMap::new();
    let mut all_report_files: Vec<report::ReportFile> = Vec::new();
    let mut line_count = 1;
    for l in v {
        match l {
            LineType::Separator => {
                all_report_files.push(report::ReportFile {
                    lines: current_report_lines,
                });
                current_report_lines = HashMap::new();
                line_count = 1;
            }
            LineType::Emptyline => {
                line_count += 1;
            }
            LineType::Details => {}
            LineType::Content(report_line) => {
                current_report_lines.insert(line_count, report_line);
                line_count += 1;
            }
        }
    }
    all_report_files.push(report::ReportFile {
        lines: current_report_lines,
    });
    return report::Report {
        report_files: all_report_files,
        filenames: filenames,
        session_mapping: session_mapping,
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_adds_two() {
        let content = "{}
[1, null, [[0, 1], [1, 0]]]


[1, null, [[0, 1], [1, 0]]]
[0, null, [[0, 0], [1, 0]]]
<<<<< end_of_chunk >>>>>
{}
[1, null, [[0, 1], [1, 0]]]


[1, null, [[0, 1], [1, 0]]]
[1, null, [[0, 1], [1, 0]]]


[1, null, [[0, 1], [1, 0]]]
[1, null, [[0, 1], [1, 0]]]


[1, null, [[0, 1], [1, 1]]]
[1, null, [[0, 1], [1, 1]]]
<<<<< end_of_chunk >>>>>
{}
[1, null, [[0, 1], [1, 0]]]
[1, null, [[0, 1], [1, 1]]]


[1, null, [[0, 1], [1, 1]]]
[1, null, [[0, 0], [1, 0]]]


[1, null, [[0, 1], [1, 0]]]
[1, null, [[0, 1], [1, 0]]]
[1, null, [[0, 1], [1, 0]]]
[1, null, [[0, 1], [1, 0]]]


[1, null, [[0, 1], [1, 0]]]
[0, null, [[0, 0], [1, 0]]]
";
        let filenames: HashMap<String, i32> = HashMap::new();
        let mut flags: HashMap<i32, Vec<String>> = HashMap::new();
        flags.insert(1, ["flag_one".to_string()].to_vec());
        flags.insert(
            0,
            ["flag_three".to_string(), "flag_two".to_string()].to_vec(),
        );
        let res = parse_report_from_str(filenames, content.to_string(), flags);
        let calc = res.calculate_per_flag_totals();
        let calc_2 = res.get_totals().unwrap();
        assert_eq!(calc_2.get_coverage().unwrap(), "90");
        assert_eq!(res.get_eof(0), 5);
        assert_eq!(res.get_eof(1), 13);
        assert_eq!(res.get_eof(2), 16);
    }
}
