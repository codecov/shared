use fraction::GenericFraction;
use fraction::ToPrimitive;

#[derive(PartialEq, Debug, Clone)]
pub enum Coverage {
    Hit,
    Miss,
    Partial(GenericFraction<i32>),
}

impl Coverage {
    pub fn get_value(&self) -> f64 {
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

    pub fn join_coverages(many_coverages: Vec<&Coverage>) -> Coverage {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn joining_coverage_works() {
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
