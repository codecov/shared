use crate::changes;
use crate::diff;
use crate::report;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use pyo3::types::PyType;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::collections::HashSet;

#[derive(Debug, Serialize)]
struct GroupImpact {
    files: Vec<GroupFileImpact>,
    group_name: String,
}

#[derive(Debug, Serialize)]
struct GroupFileImpact {
    filename: String,
    impacted_base_lines: Vec<i32>,
}

#[derive(Serialize, Deserialize, Debug)]
struct SingleFileProfilingData {
    filename: String,
    ln_ex_ct: Vec<(i32, i32)>,
}

#[derive(Serialize, Deserialize, Debug)]
struct SingleGroupProfilingData {
    count: i32,
    group_name: String,
    files: Vec<SingleFileProfilingData>,
}

#[pyclass]
pub struct ProfilingData {
    groups: Vec<SingleGroupProfilingData>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ProfilingDataJson {
    files: Vec<SingleFileProfilingData>,
    groups: Vec<SingleGroupProfilingData>,
}

#[pymethods]
impl ProfilingData {
    #[classmethod]
    pub fn load_from_json(_cls: &PyType, json_str: &str) -> PyResult<ProfilingData> {
        let json_data: Result<ProfilingDataJson, _> = serde_json::from_str(json_str);
        match json_data {
            Ok(result) => {
                return Ok(ProfilingData {
                    groups: result.groups,
                })
            }
            Err(_) => Err(PyException::new_err("Error loading full profiling data")),
        }
    }

    fn find_impacted_endpoints(
        &self,
        base_report: &report::Report,
        head_report: &report::Report,
        diff: diff::DiffInput,
    ) {
    }

    fn apply_diff_changes(&mut self, _diff: diff::DiffInput) {}
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Read;

    #[test]
    fn it_parses_data() {
        let mut contents = String::new();
        let mut file =
            File::open("tests/samples/sample_opentelem_collected.json").expect("file not there");
        file.read_to_string(&mut contents);
        let v: ProfilingDataJson = serde_json::from_str(&contents).expect("Not a valid json stuff");
        let filenames: Vec<String> = v.files.iter().map(|f| f.filename.to_owned()).collect();
        assert_eq!(
            filenames,
            vec![
                "helpers/logging_config.py",
                "services/redis.py",
                "tasks/base.py",
                "tasks/upload.py",
                "database/base.py",
                "database/engine.py",
                "database/models/core.py",
                "database/models/reports.py",
                "helpers/cache.py",
                "helpers/pathmap/pathmap.py",
                "helpers/pathmap/tree.py",
                "services/archive.py",
                "services/bots.py",
                "services/repository.py",
                "services/storage.py",
                "services/path_fixer/__init__.py",
                "services/path_fixer/fixpaths.py",
                "services/path_fixer/user_path_fixes.py",
                "services/path_fixer/user_path_includes.py",
                "services/report/__init__.py",
                "services/report/parser.py",
                "services/report/raw_upload_processor.py",
                "services/report/report_processor.py",
                "services/report/languages/base.py",
                "services/report/languages/clover.py",
                "services/report/languages/cobertura.py",
                "services/report/languages/csharp.py",
                "services/report/languages/helpers.py",
                "services/report/languages/jacoco.py",
                "services/report/languages/jetbrainsxml.py",
                "services/report/languages/mono.py",
                "services/report/languages/scoverage.py",
                "services/report/languages/vb.py",
                "services/report/languages/vb2.py",
                "services/yaml/reader.py",
                "tasks/upload_processor.py"
            ]
        );
    }
}
