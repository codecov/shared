extern crate rayon;
use crate::cov;

use fraction::GenericFraction;
use fraction::ToPrimitive;
use pyo3::prelude::*;
use rayon::prelude::*;

use serde_json::{Value};
use std::collections::HashMap;

enum CoverageType {
    Standard,
    Branch,
    Method,
}

#[derive(PartialEq, Debug)]
enum Coverage {
    Hit,
    Miss,
    Partial(GenericFraction<i32>),
}

impl Coverage {
    fn get_value(&self) -> f64 {
        match self {
            Coverage::Hit => {
                return 1.0;
            }
            Coverage::Miss => {
                return 0.0;
            }
            Coverage::Partial(f) => {
                return f.to_f64().unwrap();
            }
        }
    }

    fn join_coverages(many_coverages: Vec<&Coverage>) -> Coverage {
        let mut a: Coverage = Coverage::Miss;
        for cov in many_coverages.iter() {
            match cov {
                Coverage::Hit => return Coverage::Hit,
                Coverage::Miss => {}
                Coverage::Partial(f) => {
                    if f.to_f64().unwrap() > a.get_value() {
                        a = Coverage::Partial(*f);
                    }
                }
            }
        }
        return a;
    }
}

struct ReportLine {
    coverage: Coverage,
    coverage_type: CoverageType,
    sessions: Vec<LineSession>,
    complexity: Option<i32>, // This has to be redone
}

impl ReportLine {
    fn calculate_sessions_coverage(&self, session_ids: &Vec<i32>) -> Coverage {
        let valid_sessions: Vec<&Coverage> = self
            .sessions
            .iter()
            .filter(|k| session_ids.contains(&k.id))
            .map(|k| &k.coverage)
            .collect();
        return Coverage::join_coverages(valid_sessions);
    }
}

enum LineType {
    Content(ReportLine),
    Emptyline,
    Separator,
    Details,
}

struct LineSession {
    id: i32,
    coverage: Coverage,
    branches: i32,
    partials: Vec<i32>,
    complexity: i32,
}

pub struct ReportFile {
    lines: HashMap<i32, ReportLine>,
}

#[pyclass]
pub struct Report {
    filenames: HashMap<String, i32>,
    report_files: HashMap<i32, ReportFile>,
    session_mapping: HashMap<i32, Vec<String>>,
}

impl ReportFile {
    fn get_eof(&self) -> Option<i32> {
        return match self.lines.keys().max() {
            Some(expr) => Some(*expr),
            None => None,
        };
    }

    fn get_filtered_totals(&self, sessions: &Vec<i32>) -> cov::ReportTotals {
        let mut res = cov::ReportTotals {
            files: 1,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for (_, line) in self.lines.iter() {
            res.lines += 1;
            match line.calculate_sessions_coverage(sessions) {
                Coverage::Hit => {
                    res.hits += 1;
                }
                Coverage::Miss => {
                    res.misses += 1;
                }
                Coverage::Partial(_) => {
                    res.partials += 1;
                }
            }
        }
        return res;
    }

    fn calculate_per_flag_totals(
        &self,
        flag_mapping: &HashMap<i32, Vec<String>>,
    ) -> HashMap<String, cov::ReportTotals> {
        let mut book_reviews: HashMap<String, cov::ReportTotals> = HashMap::new();
        for (_, report_line) in self.lines.iter() {
            for sess in &report_line.sessions {
                match flag_mapping.get(&sess.id) {
                    Some(flags) => {
                        for f in flags {
                            let mut stat =
                                book_reviews
                                    .entry(f.to_string())
                                    .or_insert(cov::ReportTotals {
                                        files: 1,
                                        lines: 0,
                                        hits: 0,
                                        misses: 0,
                                        partials: 0,
                                        branches: 0,
                                        methods: 0,
                                        sessions: 0,
                                        complexity: 0,
                                        complexity_total: 0,
                                    });
                            stat.lines += 1;
                            match sess.coverage {
                                Coverage::Hit => stat.hits += 1,
                                Coverage::Miss => stat.misses += 1,
                                Coverage::Partial(_) => stat.partials += 1,
                            }
                        }
                    }
                    None => {}
                }
            }
        }
        return book_reviews;
    }

    fn get_totals(&self) -> cov::ReportTotals {
        let mut res: cov::ReportTotals = cov::ReportTotals {
            files: 1,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for (_, report_line) in self.lines.iter() {
            res.lines += 1;
            match report_line.coverage {
                Coverage::Hit => res.hits += 1,
                Coverage::Miss => res.misses += 1,
                Coverage::Partial(_) => res.partials += 1,
            }
        }
        return res;
    }
}

impl Report {
    fn get_sessions_from_flags(&self, flags: &Vec<&str>) -> Vec<i32> {
        let mut res: Vec<i32> = Vec::new();
        for (session_id, session_flags) in self.session_mapping.iter() {
            if flags.iter().any(|v| session_flags.contains(&v.to_string())) {
                res.push(*session_id); // TODO Do I have to use this * ?
            }
        }
        return res;
    }
}

#[pymethods]
impl Report {
    fn get_filtered_totals(&self, files: Vec<&str>, flags: Vec<&str>) -> cov::ReportTotals {
        let sessions = self.get_sessions_from_flags(&flags);
        let mut initial = cov::ReportTotals {
            files: 0,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for filename in files {
            let location = self.filenames.get(filename);
            if let Some(i) = location {
                match self.report_files.get(i) {
                    Some(report_file) => {
                        let some_totals = report_file.get_filtered_totals(&sessions);
                        initial.add_up(&some_totals);
                    }
                    None => {
                        panic!("Location");
                    }
                }
            }
        }
        return initial;
    }

    fn calculate_per_flag_totals(&self) -> HashMap<String, cov::ReportTotals> {
        let mut book_reviews: HashMap<String, cov::ReportTotals> = HashMap::new();
        for (_, report_file) in self.report_files.iter() {
            let file_totals = report_file.calculate_per_flag_totals(&self.session_mapping);
            for (flag_name, totals) in file_totals.iter() {
                let mut current =
                    book_reviews
                        .entry(flag_name.to_string())
                        .or_insert(cov::ReportTotals {
                            files: 0,
                            lines: 0,
                            hits: 0,
                            misses: 0,
                            partials: 0,
                            branches: 0,
                            methods: 0,
                            sessions: 0,
                            complexity: 0,
                            complexity_total: 0,
                        });
                current.files += totals.files;
                current.lines += totals.lines;
                current.hits += totals.hits;
                current.misses += totals.misses;
                current.partials += totals.partials;
                current.branches += totals.branches;
                current.methods += totals.methods;
                current.sessions += totals.sessions;
                current.complexity += totals.complexity;
                current.complexity_total += totals.complexity_total;
            }
        }
        return book_reviews;
    }

    fn get_totals(&self) -> PyResult<cov::ReportTotals> {
        let mut res: cov::ReportTotals = cov::ReportTotals {
            files: 0,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for (_, report_file) in self.report_files.iter() {
            let totals = report_file.get_totals();
            res.files += totals.files;
            res.lines += totals.lines;
            res.hits += totals.hits;
            res.misses += totals.misses;
            res.partials += totals.partials;
            res.branches += totals.branches;
            res.methods += totals.methods;
            res.sessions += totals.sessions;
            res.complexity += totals.complexity;
            res.complexity_total += totals.complexity_total;
        }
        return Ok(res);
    }
}

#[pymethods]
impl Report {
    fn get_eof(&self, file_number: i32) -> i32 {
        let file: &ReportFile = self.report_files.get(&file_number).unwrap();
        match file.get_eof() {
            Some(expr) => expr,
            None => 1,
        }
    }
}

fn parse_coverage(line: &Value) -> Coverage {
    match line {
        Value::Number(o) => {
            return if o.as_i64().unwrap() > 0 {
                Coverage::Hit
            } else {
                Coverage::Miss
            }
        }
        Value::String(s) => match s.rfind("/") {
            Some(_) => {
                let v: Vec<&str> = s.rsplit('/').collect();
                let num: i32 = v[0].parse().unwrap();
                let den: i32 = v[1].parse().unwrap();
                let f: GenericFraction<i32> = GenericFraction::new(num, den);
                return Coverage::Partial(f);
            }
            None => {
                let val: i32 = s.parse().unwrap();
                return if val > 0 {
                    Coverage::Hit
                } else {
                    Coverage::Miss
                };
            }
        },
        Value::Array(a) => panic!("Array {:?}", a),
        Value::Null => return Coverage::Miss,
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
            let mut sessions: Vec<LineSession> = Vec::new();
            for el in array_data[2].as_array().unwrap() {
                sessions.push(LineSession {
                    id: el[0].as_i64().unwrap() as i32,
                    coverage: parse_coverage(&el[1]),
                    branches: 0,
                    partials: [0].to_vec(),
                    complexity: 0,
                })
            }
            return LineType::Content(ReportLine {
                coverage: parse_coverage(&array_data[0]),
                coverage_type: CoverageType::Standard, // TODO: fix this
                sessions: sessions,
                complexity: Option::None,
            });
        }
        Value::Null => return LineType::Emptyline,
        Value::Bool(_) => panic!("{:?}", "BOOL"),
        Value::Object(_) => return LineType::Details,
    }
}

// fn parse_reportfile_from_section(section: &str) -> ReportFile {
//     let mut file_mapping: HashMap<i32, ReportLine> = HashMap::new();
//     let all_lines = section.lines();
//     let mut line_count = 0;
//     for line in all_lines {
//         if line_count == 0 {
//             let c: Map<String, Value> = serde_json::from_str(&line).unwrap();
//         } else {
//             let content = parse_line(&line);
//             match content {
//                 LineType::Emptyline => {
//                     line_count += 1;
//                 }
//                 LineType::Content(s) => {
//                     file_mapping.insert(line_count, s);
//                     line_count += 1;
//                 }
//                 LineType::Separator => {
//                     panic!("{:?}", "Separator");
//                 }
//                 LineType::Details => {
//                     panic!("{:?}", "Details");
//                 }
//             }
//         }
//         line_count += 1;
//     }
//     return ReportFile {
//         lines: file_mapping,
//     };
// }

pub fn parse_report_from_str(
    filenames: HashMap<String, i32>,
    chunks: String,
    session_mapping: HashMap<i32, Vec<String>>,
) -> Report {
    let mut book_reviews: HashMap<i32, ReportFile> = HashMap::new();
    let v: Vec<_> = chunks.par_lines().map(|line| parse_line(&line)).collect();
    let mut current_report_lines: HashMap<i32, ReportLine> = HashMap::new();
    let mut all_report_files: Vec<ReportFile> = Vec::new();
    let mut line_count = 1;
    for l in v {
        match l {
            LineType::Separator => {
                all_report_files.push(ReportFile {
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
    all_report_files.push(ReportFile {
        lines: current_report_lines,
    });
    let mut file_count: i32 = 0;
    for report_file in all_report_files {
        book_reviews.insert(file_count, report_file);
        file_count += 1;
    }
    println!("{:?}", book_reviews.len());
    return Report {
        report_files: book_reviews,
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

    #[test]
    fn joining_works() {
        let v = Coverage::join_coverages(vec![
            &Coverage::Miss,
            &Coverage::Hit,
            &Coverage::Partial(GenericFraction::new(3, 10)),
        ]);
        assert_eq!(v, Coverage::Hit);
        let k = Coverage::join_coverages(vec![
            &Coverage::Miss,
            &Coverage::Partial(GenericFraction::new(3, 10)),
        ]);
        assert_eq!(k, Coverage::Partial(GenericFraction::new(3, 10)));
    }
}
