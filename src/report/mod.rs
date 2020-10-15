extern crate rayon;

use fraction::GenericFraction;
use pyo3::prelude::*;
use rayon::prelude::*;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::HashMap;

enum CoverageType {
    Standard,
    Branch,
    Method,
}

enum Coverage {
    Hit,
    Miss,
    Partial(GenericFraction<u64>),
}

struct ReportLine {
    coverage: Coverage,
    coverage_type: CoverageType,
    sessions: Vec<LineSession>,
    messages: Option<u64>,
    complexity: Option<u64>, // This has to be redone
}

enum LineType {
    Content(ReportLine),
    Emptyline,
    Separator,
    Details,
}

struct LineSession {
    id: u64,
    coverage: Coverage,
    branches: u64,
    partials: Vec<u64>,
    complexity: u64,
}

#[pyclass]
#[derive(Serialize, Deserialize)]
struct ReportTotals {
    #[pyo3(get)]
    files: u64,
    lines: u64,
    #[pyo3(get)]
    hits: u64,
    misses: u64,
    partials: u64,
    branches: u64,
    methods: u64,
    messages: u64,
    sessions: u64,
    complexity: u64,
    complexity_total: u64,
}

#[pyclass]
pub struct ReportFile {
    lines: HashMap<u64, ReportLine>,
}

#[pyclass]
pub struct Report {
    filenames: HashMap<String, u64>,
    report_files: HashMap<u64, ReportFile>,
    session_mapping: HashMap<u64, Vec<String>>
}

impl ReportFile {
    fn get_filtered_totals(&self, flags: &Vec<&str>) -> ReportTotals {
        ReportTotals {
            files: 1,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            messages: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        }
    }

    fn calculate_per_flag_totals(
        &self,
        flag_mapping: &HashMap<u64, Vec<String>>,
    ) -> HashMap<String, ReportTotals> {
        let mut book_reviews: HashMap<String, ReportTotals> = HashMap::new();
        for (line_number, report_line) in self.lines.iter() {
            for sess in &report_line.sessions {
                match flag_mapping.get(&sess.id) {
                    Some(flags) => {
                        for f in flags {
                            let mut stat =
                                book_reviews.entry(f.to_string()).or_insert(ReportTotals {
                                    files: 1,
                                    lines: 0,
                                    hits: 0,
                                    misses: 0,
                                    partials: 0,
                                    branches: 0,
                                    methods: 0,
                                    messages: 0,
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

    fn get_totals(&self) -> ReportTotals {
        let mut res: ReportTotals = ReportTotals {
            files: 1,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            messages: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for (line_number, report_line) in self.lines.iter() {
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

#[pymethods]
impl Report {
    fn get_filtered_totals(&self, files: Vec<&str>, flags: Vec<&str>) -> ReportTotals {
        let mut initial = ReportTotals {
            files: 0,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            messages: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for filename in files {
            let location = self.filenames.get(filename);
            if let Some(i) = location {
                match self.report_files.get(i) {
                    Some(report_file) => {
                        let some_totals = report_file.get_filtered_totals(&flags);
                        initial.files += some_totals.files;
                        initial.lines += some_totals.lines;
                        initial.hits += some_totals.hits;
                        initial.misses += some_totals.misses;
                        initial.partials += some_totals.partials;
                        initial.branches += some_totals.branches;
                        initial.methods += some_totals.methods;
                        initial.messages += some_totals.messages;
                        initial.sessions += some_totals.sessions;
                        initial.complexity += some_totals.complexity;
                        initial.complexity_total += some_totals.complexity_total;
                    }
                    None => {panic!("Location");}
                }
            }
        }
        return initial;
    }

    fn calculate_per_flag_totals(
        &self
    ) -> HashMap<String, ReportTotals> {
        let mut book_reviews: HashMap<String, ReportTotals> = HashMap::new();
        for (key, report_file) in self.report_files.iter() {
            let file_totals = report_file.calculate_per_flag_totals(&self.session_mapping);
            for (flag_name, totals) in file_totals.iter() {
                let mut current =
                    book_reviews
                        .entry(flag_name.to_string())
                        .or_insert(ReportTotals {
                            files: 0,
                            lines: 0,
                            hits: 0,
                            misses: 0,
                            partials: 0,
                            branches: 0,
                            methods: 0,
                            messages: 0,
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
                current.messages += totals.messages;
                current.sessions += totals.sessions;
                current.complexity += totals.complexity;
                current.complexity_total += totals.complexity_total;
            }
        }
        return book_reviews;
    }

    fn get_totals(&self) -> ReportTotals {
        let mut res: ReportTotals = ReportTotals {
            files: 0,
            lines: 0,
            hits: 0,
            misses: 0,
            partials: 0,
            branches: 0,
            methods: 0,
            messages: 0,
            sessions: 0,
            complexity: 0,
            complexity_total: 0,
        };
        for (key, report_file) in self.report_files.iter() {
            let totals = report_file.get_totals();
            res.files += totals.files;
            res.lines += totals.lines;
            res.hits += totals.hits;
            res.misses += totals.misses;
            res.partials += totals.partials;
            res.branches += totals.branches;
            res.methods += totals.methods;
            res.messages += totals.messages;
            res.sessions += totals.sessions;
            res.complexity += totals.complexity;
            res.complexity_total += totals.complexity_total;
        }
        return res;
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
                let num: u64 = v[0].parse().unwrap();
                let den: u64 = v[1].parse().unwrap();
                let f: GenericFraction<u64> = GenericFraction::new(num, den);
                return Coverage::Partial(f);
            }
            None => {
                let val: u64 = s.parse().unwrap();
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
                    id: el[0].as_u64().unwrap(),
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
                messages: Option::None,
                complexity: Option::None,
            });
        }
        Value::Null => return LineType::Emptyline,
        Value::Bool(_) => panic!("{:?}", "BOOL"),
        Value::Object(_) => return LineType::Details,
    }
}

fn parse_reportfile_from_section(section: &str) -> ReportFile {
    let mut file_mapping: HashMap<u64, ReportLine> = HashMap::new();
    let all_lines = section.lines();
    let mut line_count = 0;
    for line in all_lines {
        if line_count == 0 {
            let c: Map<String, Value> = serde_json::from_str(&line).unwrap();
        } else {
            let content = parse_line(&line);
            match content {
                LineType::Emptyline => {
                    line_count += 1;
                }
                LineType::Content(s) => {
                    file_mapping.insert(line_count, s);
                    line_count += 1;
                }
                LineType::Separator => {
                    panic!("{:?}", "Separator");
                }
                LineType::Details => {
                    panic!("{:?}", "Details");
                }
            }
        }
        line_count += 1;
    }
    return ReportFile {
        lines: file_mapping,
    };
}

pub fn parse_report_from_str(filenames: HashMap<String, u64>, chunks: String, session_mapping: HashMap<u64, Vec<String>>) -> Report {
    let mut book_reviews: HashMap<u64, ReportFile> = HashMap::new();
    let v: Vec<_> = chunks.par_lines().map(|line| parse_line(&line)).collect();
    let mut current_report_lines: HashMap<u64, ReportLine> = HashMap::new();
    let mut all_report_files: Vec<ReportFile> = Vec::new();
    let mut line_count = 1;
    for l in v {
        match l {
            LineType::Separator => {
                all_report_files.push(ReportFile {
                    lines: current_report_lines,
                });
                current_report_lines = HashMap::new();
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
    let mut file_count: u64 = 0;
    for report_file in all_report_files {
        book_reviews.insert(file_count, report_file);
        file_count += 1;
    }
    println!("{:?}", book_reviews.len());
    return Report {
        report_files: book_reviews,
        filenames: filenames,
        session_mapping: session_mapping
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
        let filenames: HashMap<String, u64> = HashMap::new();
        let mut flags: HashMap<u64, Vec<String>> = HashMap::new();
        flags.insert(1, ["flag_one".to_string()].to_vec());
        flags.insert(
            0,
            ["flag_three".to_string(), "flag_two".to_string()].to_vec(),
        );
        let res = parse_report_from_str(filenames, content.to_string(), flags);
        let calc = res.calculate_per_flag_totals();
        let calc_2 = res.get_totals();
        println!("{}", serde_json::to_string(&calc).unwrap());
        println!("{}", serde_json::to_string(&calc_2).unwrap());
        panic!("{:?}", "Error test succeeded");
    }
}
