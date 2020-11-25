extern crate rayon;
use crate::cov;
use crate::file;
use crate::line;
use crate::report;

use fraction::GenericFraction;
use rayon::prelude::*;

use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug)]
enum LineType {
    Content(line::ReportLine),
    Emptyline,
    Separator,
    Details,
}

#[derive(Debug)]
pub enum ParsingError {
    UnexpectedValue,
}

fn parse_coverage_type(val: &Value) -> Result<line::CoverageType, ParsingError> {
    match val {
        Value::String(v) => {
            if v == "m" {
                return Ok(line::CoverageType::Method);
            }
            if v == "b" {
                return Ok(line::CoverageType::Branch);
            }
            return Err(ParsingError::UnexpectedValue);
        }
        Value::Null => return Ok(line::CoverageType::Standard),
        _ => {
            return Err(ParsingError::UnexpectedValue);
        }
    }
}

fn parse_coverage(line: &Value) -> Result<cov::Coverage, ParsingError> {
    match line {
        Value::Number(o) => {
            return if o.as_i64().ok_or(ParsingError::UnexpectedValue)? > 0 {
                Ok(cov::Coverage::Hit)
            } else {
                Ok(cov::Coverage::Miss)
            }
        }
        Value::String(s) => match s.rfind("/") {
            Some(_) => {
                let v: Vec<&str> = s.rsplit('/').collect();
                let num: i32 = v[0].parse().unwrap();
                let den: i32 = v[1].parse().unwrap();
                if num == den {
                    return Ok(cov::Coverage::Hit);
                }
                let f: GenericFraction<i32> = GenericFraction::new(num, den);
                return Ok(cov::Coverage::Partial(f));
            }
            None => {
                let val: i32 = s.parse().unwrap();
                return if val > 0 {
                    Ok(cov::Coverage::Hit)
                } else {
                    Ok(cov::Coverage::Miss)
                };
            }
        },
        Value::Array(_) => {
            return Err(ParsingError::UnexpectedValue);
        }
        Value::Null => return Ok(cov::Coverage::Miss),
        Value::Bool(b) => {
            if *b {
                return Ok(cov::Coverage::Partial(GenericFraction::new(1, 2)));
            }
            return Err(ParsingError::UnexpectedValue);
        }
        Value::Object(_) => {
            return Err(ParsingError::UnexpectedValue);
        }
    }
}

fn parse_complexity(val: &Value) -> Result<Option<line::Complexity>, ParsingError> {
    match val {
        Value::Number(o) => {
            return Ok(Some(line::Complexity::SingleComplexity(
                o.as_i64().unwrap() as i32,
            )));
        }
        Value::String(_) => return Err(ParsingError::UnexpectedValue),
        Value::Array(a) => {
            return Ok(Some(line::Complexity::TotalComplexity((
                a[0].as_i64().ok_or(ParsingError::UnexpectedValue)? as i32,
                a[1].as_i64().ok_or(ParsingError::UnexpectedValue)? as i32,
            ))));
        }
        Value::Null => return Ok(None),
        Value::Bool(_) => return Err(ParsingError::UnexpectedValue),
        Value::Object(_) => return Err(ParsingError::UnexpectedValue),
    }
}

fn parse_line(line: &str) -> Result<LineType, ParsingError> {
    if line.is_empty() {
        return Ok(LineType::Emptyline);
    }
    if line == "<<<<< end_of_chunk >>>>>" {
        return Ok(LineType::Separator);
    }
    match serde_json::from_str(&line).unwrap() {
        Value::Number(_) => return Err(ParsingError::UnexpectedValue),
        Value::String(_) => return Err(ParsingError::UnexpectedValue),
        Value::Array(array_data) => {
            let mut sessions: Vec<line::LineSession> = Vec::new();
            if array_data.len() > 2 {
                for el in array_data[2]
                    .as_array()
                    .ok_or(ParsingError::UnexpectedValue)?
                {
                    let el_as_array = el.as_array().ok_or(ParsingError::UnexpectedValue)?;
                    sessions.push(line::LineSession {
                        id: el_as_array[0]
                            .as_i64()
                            .ok_or(ParsingError::UnexpectedValue)?
                            as i32,
                        coverage: parse_coverage(&el[1])?,
                        branches: 0,
                        partials: [0].to_vec(),
                        complexity: parse_complexity(if el_as_array.len() > 4 {
                            &el_as_array[4]
                        } else {
                            &Value::Null
                        })?,
                    })
                }
            }
            return Ok(LineType::Content(line::ReportLine {
                coverage: parse_coverage(&array_data[0])?,
                coverage_type: if array_data.len() > 1 {
                    parse_coverage_type(&array_data[1])?
                } else {
                    line::CoverageType::Standard
                },
                sessions: sessions,
                complexity: parse_complexity(if array_data.len() > 4 {
                    &array_data[4]
                } else {
                    &Value::Null
                })?,
            }));
        }
        Value::Null => return Ok(LineType::Emptyline),
        Value::Bool(_) => return Err(ParsingError::UnexpectedValue),
        Value::Object(_) => return Ok(LineType::Details),
    }
}

pub fn parse_report_from_str(
    filenames: HashMap<String, i32>,
    chunks: String,
    session_mapping: HashMap<i32, Vec<String>>,
) -> Result<report::Report, ParsingError> {
    let v: Vec<_> = chunks.par_lines().map(|line| parse_line(&line)).collect();
    if v.len() == 0 {
        return Ok(report::Report {
            report_files: Vec::new(),
            filenames: filenames,
            session_mapping: session_mapping,
        });
    }
    let mut current_report_lines: HashMap<i32, line::ReportLine> = HashMap::new();
    let mut all_report_files: Vec<file::ReportFile> = Vec::new();
    let mut line_count = 1;
    for result in v {
        match result {
            Ok(l) => match l {
                LineType::Separator => {
                    all_report_files.push(file::ReportFile {
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
            },
            Err(err) => return Err(err),
        }
    }
    all_report_files.push(file::ReportFile {
        lines: current_report_lines,
    });
    return Ok(report::Report {
        report_files: all_report_files,
        filenames: filenames,
        session_mapping: session_mapping,
    });
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
        let res = parse_report_from_str(filenames, content.to_string(), flags)
            .expect("Unable to parse report");
        let calc = res.calculate_per_flag_totals();
        let calc_2 = res.get_simple_totals().unwrap();
        assert_eq!(calc_2.get_coverage().unwrap(), Some("90.00000".to_string()));
        assert_eq!(res.get_eof(0), 5);
        assert_eq!(res.get_eof(1), 13);
        assert_eq!(res.get_eof(2), 16);
    }

    #[test]
    fn parses_empty_report() {
        let filenames: HashMap<String, i32> = HashMap::new();
        let mut flags: HashMap<i32, Vec<String>> = HashMap::new();
        flags.insert(1, ["flag_one".to_string()].to_vec());
        flags.insert(
            0,
            ["flag_three".to_string(), "flag_two".to_string()].to_vec(),
        );
        let res = parse_report_from_str(filenames, "".to_string(), flags).expect("Unable to parse report");
        assert_eq!(res.report_files.len(), 0);
        let calc = res.calculate_per_flag_totals();
        let calc_2 = res.get_simple_totals().unwrap();
        assert_eq!(calc_2.get_coverage().unwrap(), None);
    }

    #[test]
    fn parse_line_simple_case() {
        let res = parse_line("[1, null, [[0, 1], [1, 0]]]").expect("Unable to parse line");
        match res {
            LineType::Content(l) => {
                assert_eq!(l.coverage, cov::Coverage::Hit);
                assert_eq!(l.coverage_type, line::CoverageType::Standard);
            }
            _ => {
                panic!("Bad res");
            }
        }
    }

    #[test]
    fn parse_line_boolean_case() {
        let res = parse_line("[true, \"b\", [[0, true, null, null, null]]]")
            .expect("Unable to parse line");
        match res {
            LineType::Content(l) => {
                assert_eq!(
                    l.coverage,
                    cov::Coverage::Partial(GenericFraction::new(1, 2))
                );
                assert_eq!(l.coverage_type, line::CoverageType::Branch);
            }
            _ => {
                panic!("Bad res");
            }
        }
    }

    #[test]
    fn parse_line_bad_line() {
        let res = parse_line("[null, \"b\", [[null, true, null, null, null]]]")
            .expect_err("Line should have thrown an error");
    }
}
