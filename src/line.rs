use crate::cov;

#[derive(Debug, Clone)]
pub enum CoverageType {
    Standard,
    Branch,
    Method,
}

#[derive(Debug, Clone)]
pub enum Complexity {
    TotalComplexity((i32, i32)),
    SingleComplexity(i32),
}

#[derive(Debug, Clone)]
pub struct LineSession {
    pub id: i32,
    pub coverage: cov::Coverage,
    pub branches: i32,
    pub partials: Vec<i32>,
    pub complexity: Option<Complexity>,
}

#[derive(Debug)]
pub struct ReportLine {
    pub coverage: cov::Coverage,
    pub coverage_type: CoverageType,
    pub sessions: Vec<LineSession>,
    pub complexity: Option<Complexity>,
}

impl ReportLine {
    pub fn filter_by_session_ids(&self, session_ids: &Vec<i32>) -> ReportLine {
        let valid_sessions: Vec<LineSession> = self
            .sessions
            .iter()
            .filter(|k| session_ids.contains(&k.id))
            .map(|x| x.clone())
            .collect();
        ReportLine {
            coverage: self.calculate_sessions_coverage(&valid_sessions),
            coverage_type: self.coverage_type.clone(),
            complexity: self.calculate_sessions_complexity(&valid_sessions),
            sessions: valid_sessions,
        }
    }

    pub fn calculate_sessions_coverage(&self, sessions: &Vec<LineSession>) -> cov::Coverage {
        let valid_sessions: Vec<&cov::Coverage> = sessions.iter().map(|k| &k.coverage).collect();
        return cov::Coverage::join_coverages(valid_sessions);
    }

    pub fn calculate_sessions_complexity(&self, sessions: &Vec<LineSession>) -> Option<Complexity> {
        let complexities: Vec<(i32, i32)> = sessions
            .iter()
            .filter_map(|k| match &k.complexity {
                Some(x) => match x {
                    Complexity::SingleComplexity(v) => Some((*v, 0)),
                    Complexity::TotalComplexity(v) => Some((v.0, v.1)),
                },
                None => None,
            })
            .collect();
        let complexity_total = complexities.iter().map(|x| x.1).max();
        match complexity_total {
            None => return None,
            Some(total) => {
                let complexity = complexities.iter().map(|x| x.0).max().unwrap();
                if total > 0 {
                    return Some(Complexity::TotalComplexity((complexity, total)));
                }
                return Some(Complexity::SingleComplexity(complexity));
            }
        }
    }
}
