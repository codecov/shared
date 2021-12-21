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
    NoFile,
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
            return match o.as_i64() {
                Some(number) => {
                    if number > 0 {
                        Ok(cov::Coverage::Hit)
                    } else if number == -1 {
                        Ok(cov::Coverage::Ignore)
                    } else {
                        Ok(cov::Coverage::Miss)
                    }
                }
                None => match o.as_f64() {
                    Some(alternative_number) => {
                        if alternative_number > 0.0 {
                            Ok(cov::Coverage::Hit)
                        } else {
                            Ok(cov::Coverage::Miss)
                        }
                    }
                    None => Err(ParsingError::UnexpectedValue),
                },
            };
        }
        Value::String(s) => match s.rfind("/") {
            Some(_) => {
                let v: Vec<&str> = s.split('/').collect();
                let num: i32 = v[0].parse().unwrap();
                let den: i32 = v[1].parse().unwrap();
                if num == den {
                    return Ok(cov::Coverage::Hit);
                }
                if num == 0 {
                    return Ok(cov::Coverage::Miss);
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
        Value::Null => return Ok(cov::Coverage::Ignore),
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
        Value::Null => return Ok(LineType::NoFile),
        Value::Bool(_) => return Err(ParsingError::UnexpectedValue),
        Value::Object(_) => return Ok(LineType::Details),
    }
}

pub fn parse_report_from_str(
    filenames: HashMap<String, i32>,
    chunks: &str,
    session_mapping: HashMap<i32, Vec<String>>,
) -> Result<report::Report, ParsingError> {
    let all_lines_with_errors: Vec<_> = chunks.par_lines().map(|line| parse_line(&line)).collect();
    let all_lines_or_errors: Result<Vec<LineType>, _> = all_lines_with_errors.into_iter().collect();
    let all_lines = all_lines_or_errors?;
    if all_lines.len() == 0 {
        return Ok(report::Report {
            report_files: HashMap::new(),
            session_mapping: session_mapping,
        });
    }
    let mut current_report_lines: Option<HashMap<i32, line::ReportLine>> = None;
    let mut all_report_files: Vec<Option<file::ReportFile>> = Vec::new();
    let mut line_count = 1;
    for line in all_lines {
        match line {
            LineType::Separator => {
                all_report_files.push(match current_report_lines {
                    Some(lines) => Some(file::ReportFile { lines }),
                    None => None,
                });
                current_report_lines = None;
                line_count = 1;
            }
            LineType::Emptyline => {
                line_count += 1;
            }
            LineType::Details => {
                current_report_lines = Some(HashMap::new());
            }
            LineType::NoFile => {
                current_report_lines = None;
            }
            LineType::Content(report_line) => {
                match current_report_lines.as_mut() {
                    Some(lines) => {
                        lines.insert(line_count, report_line);
                    }
                    None => {}
                }
                line_count += 1;
            }
        }
    }
    all_report_files.push(match current_report_lines {
        Some(v) => Some(file::ReportFile { lines: v }),
        None => None,
    });
    let number_to_filename: HashMap<i32, String> = filenames
        .iter()
        .map(|(x, y)| (*y, x.to_string()))
        .into_iter()
        .collect();
    let filename_to_mapping: HashMap<String, file::ReportFile> = all_report_files
        .into_iter()
        .enumerate()
        .filter_map(|(current_count, value)| match value {
            Some(file) => {
                let filename = number_to_filename.get(&(current_count as i32));
                match filename {
                    Some(val) => Some((val.to_string(), file)),
                    None => None,
                }
            }
            None => None,
        })
        .into_iter()
        .collect();
    return Ok(report::Report {
        report_files: filename_to_mapping,
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
        let filenames: HashMap<String, i32> = vec![
            ("file1.go".to_string(), 0),
            ("file_two.go".to_string(), 1),
            ("file_iii.go".to_string(), 2),
        ]
        .into_iter()
        .collect();
        let mut flags: HashMap<i32, Vec<String>> = HashMap::new();
        flags.insert(1, ["flag_one".to_string()].to_vec());
        flags.insert(
            0,
            ["flag_three".to_string(), "flag_two".to_string()].to_vec(),
        );
        let res = parse_report_from_str(filenames, content, flags).expect("Unable to parse report");
        let calc = res.calculate_per_flag_totals();
        assert!(calc.contains_key("flag_one"));
        let calc_2 = res.get_simple_totals().unwrap();
        assert_eq!(calc_2.get_coverage().unwrap(), Some("90.00000".to_string()));
    }

    #[test]
    fn parses_report_with_null_chunks() {
        let content = "{}
[1, null, [[0, 1], [1, 0]]]


[1, null, [[0, 1], [1, 0]]]
[0, null, [[0, 0], [1, 0]]]
<<<<< end_of_chunk >>>>>
null
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
        let filenames: HashMap<String, i32> = vec![
            ("file1.go".to_string(), 0),
            ("file_two.go".to_string(), 1),
            ("file_iii.go".to_string(), 2),
        ]
        .into_iter()
        .collect();
        let flags: HashMap<i32, Vec<String>> = vec![
            (
                0,
                ["flag_three".to_string(), "flag_two".to_string()].to_vec(),
            ),
            (1, vec!["flag_one".to_string()]),
        ]
        .into_iter()
        .collect();
        let res = parse_report_from_str(filenames, content, flags).expect("Unable to parse report");
        let calc_2 = res.get_simple_totals().unwrap();
        assert_eq!(calc_2.get_coverage().unwrap(), Some("84.61538".to_string()));
        assert_eq!(calc_2.files, 2);
        assert_eq!(calc_2.hits, 11);
        assert_eq!(calc_2.lines, 13);
        let involved_filenames: Vec<String> =
            res.report_files.keys().map(|x| x.to_string()).collect();
        assert_eq!(involved_filenames.len(), 2);
        assert_eq!(
            res.report_files.get("file1.go").unwrap().get_totals().hits,
            2
        );
        assert_eq!(
            res.report_files
                .get("file1.go")
                .unwrap()
                .get_totals()
                .misses,
            1
        );
        assert_eq!(
            res.report_files
                .get("file_iii.go")
                .unwrap()
                .get_totals()
                .hits,
            9
        );
        assert_eq!(
            res.report_files
                .get("file_iii.go")
                .unwrap()
                .get_totals()
                .misses,
            1
        );
        assert!(involved_filenames.contains(&"file1.go".to_string()));
        assert!(involved_filenames.contains(&"file_iii.go".to_string()));
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
        let res = parse_report_from_str(filenames, "", flags).expect("Unable to parse report");
        assert_eq!(res.report_files.len(), 0);
        let calc = res.calculate_per_flag_totals();
        assert!(calc.is_empty());
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
    fn parse_line_huge_number_case() {
        // This is just a line that doesn't fit in i64. Unfortunately, the JSON library only goes up to
        // u64. We are just parsing as a float on those cases because f64 can handle knowing
        // if a number if higher than zero just fine, and that's what python does anyway
        let res = parse_line("[18446744073709551615, null, [[23, 18446744073709551615]]]")
            .expect("Unable to parse line");
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
    fn parse_line_method_line() {
        let res = parse_line("[1, \"m\", [[0, 1], [1, 1]]]").expect("Unable to parse line");
        match res {
            LineType::Content(l) => {
                assert_eq!(l.coverage, cov::Coverage::Hit);
                assert_eq!(l.coverage_type, line::CoverageType::Method);
            }
            _ => {
                panic!("Bad res");
            }
        }
    }

    #[test]
    fn parse_line_unusual_zero_case() {
        // Some zero
        let res =
            parse_line("[0.0, null, [[23, 18446744073709551615]]]").expect("Unable to parse line");
        match res {
            LineType::Content(l) => {
                assert_eq!(l.coverage, cov::Coverage::Miss);
                assert_eq!(l.coverage_type, line::CoverageType::Standard);
            }
            _ => {
                panic!("Bad res");
            }
        }
    }

    #[test]
    fn parse_coverage_unusual_numbers() {
        // Some zero
        assert_eq!(
            cov::Coverage::Miss,
            parse_coverage(&serde_json::from_str("0.0").unwrap())
                .expect("Unable to parse coverage")
        );
        assert_eq!(
            cov::Coverage::Miss,
            parse_coverage(&serde_json::from_str("0").unwrap()).expect("Unable to parse coverage")
        );
        assert_eq!(
            cov::Coverage::Ignore,
            parse_coverage(&serde_json::from_str("-1").unwrap()).expect("Unable to parse coverage")
        );
        assert_eq!(
            cov::Coverage::Hit,
            parse_coverage(&serde_json::from_str("0.5").unwrap())
                .expect("Unable to parse coverage")
        );
        assert_eq!(
            cov::Coverage::Hit,
            parse_coverage(&serde_json::from_str("18446744073709551615").unwrap())
                .expect("Unable to parse coverage")
        );
        // Slightly higher than u64 limit
        assert_eq!(
            cov::Coverage::Hit,
            parse_coverage(&serde_json::from_str("18446744073709551699").unwrap())
                .expect("Unable to parse coverage")
        );
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
    fn parse_line_empty_lines() {
        let res = parse_line("[null, \"b\", [[157, null]]]").expect("Unable to parse line");
        match res {
            LineType::Content(l) => {
                assert_eq!(l.coverage, cov::Coverage::Ignore);
                assert_eq!(l.coverage_type, line::CoverageType::Branch);
            }
            _ => {
                panic!("Bad res");
            }
        }
    }

    #[test]
    fn parse_line_bad_line() {
        let _res = parse_line("[1, \"b\", [[null, true, null, null, null]]]")
            .expect_err("Line should have thrown an error");
    }
    #[test]
    fn parse_coverage_sample_different_fractions() {
        let actual_partial = parse_coverage(&serde_json::from_str("\"1/2\"").unwrap())
            .expect("should have parsed correctly");
        assert_eq!(
            actual_partial,
            cov::Coverage::Partial(GenericFraction::new(1, 2))
        );
        let actual_hit = parse_coverage(&serde_json::from_str("\"3/3\"").unwrap())
            .expect("should have parsed correctly");
        assert_eq!(actual_hit, cov::Coverage::Hit);
        let actual_miss = parse_coverage(&serde_json::from_str("\"0/4\"").unwrap())
            .expect("should have parsed correctly");
        assert_eq!(actual_miss, cov::Coverage::Miss);
    }
}
