extern crate rayon;
use crate::cov;
use crate::report;

use fraction::GenericFraction;
use rayon::prelude::*;

use serde_json::Value;
use std::collections::HashMap;

enum LineType {
    Content(report::ReportLine),
    Emptyline,
    Separator,
    Details,
}

fn parse_coverage_type(val: &Value) -> report::CoverageType {
    match val {
        Value::String(v) => {
            if v == "m" {
                return report::CoverageType::Method;
            }
            if v == "b" {
                return report::CoverageType::Branch;
            }
            panic!("Unexpected coverage_type {:?}", v);
        }
        Value::Null => return report::CoverageType::Standard,
        _ => {
            panic!("{:?}", val);
        }
    }
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

fn parse_complexity(val: &Value) -> Option<report::Complexity> {
    match val {
        Value::Number(o) => {
            return Some(report::Complexity::SingleComplexity(
                o.as_i64().unwrap() as i32
            ));
        }
        Value::String(s) => panic!("Unexpected complexity {:?}", s),
        Value::Array(a) => {
            return Some(report::Complexity::TotalComplexity((
                a[0].as_i64().unwrap() as i32,
                a[1].as_i64().unwrap() as i32,
            )));
        }
        Value::Null => return None,
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
                    complexity: parse_complexity(if array_data.len() > 4 {
                        &array_data[4]
                    } else {
                        &Value::Null
                    }),
                })
            }
            return LineType::Content(report::ReportLine {
                coverage: parse_coverage(&array_data[0]),
                coverage_type: parse_coverage_type(&array_data[1]), // TODO: fix this
                sessions: sessions,
                complexity: parse_complexity(if array_data.len() > 4 {
                    &array_data[4]
                } else {
                    &Value::Null
                }),
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
        assert_eq!(calc_2.get_coverage().unwrap(), Some("90".to_string()));
        assert_eq!(res.get_eof(0), 5);
        assert_eq!(res.get_eof(1), 13);
        assert_eq!(res.get_eof(2), 16);
    }
}
