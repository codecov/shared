use crate::cov;

#[derive(Debug, Clone, PartialEq)]
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
    pub complexity: Option<Complexity>,
}

#[derive(Debug, Clone)]
pub struct ReportLine {
    pub coverage: cov::Coverage,
    pub coverage_type: CoverageType,
    pub sessions: Vec<LineSession>,
    pub complexity: Option<Complexity>,
}

impl ReportLine {
    pub fn filter_by_session_ids(&self, session_ids: &Vec<i32>) -> Option<ReportLine> {
        let valid_sessions: Vec<LineSession> = self
            .sessions
            .iter()
            .filter(|k| session_ids.contains(&k.id))
            .map(|x| x.clone())
            .collect();
        if valid_sessions.is_empty() {
            return None;
        }
        let coverage = self.calculate_sessions_coverage(&valid_sessions);
        if let cov::Coverage::Ignore = coverage {
            return None;
        }
        Some(ReportLine {
            coverage: coverage,
            coverage_type: self.coverage_type.clone(),
            complexity: self.calculate_sessions_complexity(&valid_sessions),
            sessions: valid_sessions,
        })
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

#[cfg(test)]
mod tests {
    use super::*;
    use fraction::GenericFraction;

    #[test]
    fn filter_by_session_ids_works() {
        let a = ReportLine {
            coverage: cov::Coverage::Hit,
            coverage_type: CoverageType::Standard,
            sessions: vec![
                LineSession {
                    id: 0,
                    coverage: cov::Coverage::Miss,
                    complexity: None,
                },
                LineSession {
                    id: 1,
                    coverage: cov::Coverage::Ignore,
                    complexity: None,
                },
                LineSession {
                    id: 2,
                    coverage: cov::Coverage::Partial(GenericFraction::new(3, 10)),
                    complexity: None,
                },
                LineSession {
                    id: 3,
                    coverage: cov::Coverage::Hit,
                    complexity: None,
                },
            ],
            complexity: None,
        };
        let res_only_zero = a.filter_by_session_ids(&vec![0]).unwrap();
        assert_eq!(res_only_zero.coverage, cov::Coverage::Miss);
        assert_eq!(res_only_zero.coverage_type, CoverageType::Standard);
        assert_eq!(res_only_zero.sessions.len(), 1);
        assert!(res_only_zero.complexity.is_none());
        assert!(a.filter_by_session_ids(&vec![1]).is_none());
        let res_only_two = a.filter_by_session_ids(&vec![2]).unwrap();
        assert_eq!(
            res_only_two.coverage,
            cov::Coverage::Partial(GenericFraction::new(3, 10))
        );
        assert_eq!(res_only_two.coverage_type, CoverageType::Standard);
        assert_eq!(res_only_two.sessions.len(), 1);
        assert!(res_only_two.complexity.is_none());
        let res_only_three = a.filter_by_session_ids(&vec![3]).unwrap();
        assert_eq!(res_only_three.coverage, cov::Coverage::Hit);
        assert_eq!(res_only_three.coverage_type, CoverageType::Standard);
        assert_eq!(res_only_three.sessions.len(), 1);
        assert!(res_only_three.complexity.is_none());
        let res_zero_and_one = a.filter_by_session_ids(&vec![0, 1]).unwrap();
        assert_eq!(res_zero_and_one.coverage, cov::Coverage::Miss);
        assert_eq!(res_zero_and_one.coverage_type, CoverageType::Standard);
        assert_eq!(res_zero_and_one.sessions.len(), 2);
        assert!(res_zero_and_one.complexity.is_none());
        let res_two_and_three = a.filter_by_session_ids(&vec![2, 3]).unwrap();
        assert_eq!(res_two_and_three.coverage, cov::Coverage::Hit);
        assert_eq!(res_two_and_three.coverage_type, CoverageType::Standard);
        assert_eq!(res_two_and_three.sessions.len(), 2);
        assert!(res_two_and_three.complexity.is_none());
        let res_one_and_two_and_three_and_zero =
            a.filter_by_session_ids(&vec![0, 1, 2, 3]).unwrap();
        assert_eq!(
            res_one_and_two_and_three_and_zero.coverage,
            cov::Coverage::Hit
        );
        assert_eq!(
            res_one_and_two_and_three_and_zero.coverage_type,
            CoverageType::Standard
        );
        assert_eq!(res_one_and_two_and_three_and_zero.sessions.len(), 4);
        assert!(res_one_and_two_and_three_and_zero.complexity.is_none());
        assert!(a.filter_by_session_ids(&vec![5]).is_none());
        assert!(a.filter_by_session_ids(&vec![1, 5]).is_none());
    }
}
