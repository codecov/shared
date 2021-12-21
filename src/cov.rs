use fraction::GenericFraction;
use fraction::ToPrimitive;
use serde::ser::{Serialize, Serializer};

#[derive(PartialEq, Debug, Clone)]
pub enum Coverage {
    Hit,
    Miss,
    Partial(GenericFraction<i32>),
    Ignore,
}

impl Coverage {
    fn as_char(&self) -> char {
        return match self {
            Coverage::Hit => 'h',
            Coverage::Miss => 'm',
            Coverage::Partial(_) => 'p',
            Coverage::Ignore => 'i',
        };
    }
}

impl Serialize for Coverage {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_char(self.as_char())
    }
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
            Coverage::Ignore => {
                return -1.0;
            }
        }
    }

    pub fn join_coverages(many_coverages: Vec<&Coverage>) -> Coverage {
        let mut a: Coverage = Coverage::Ignore;
        for cov in many_coverages.iter() {
            match cov {
                Coverage::Hit => return Coverage::Hit,
                Coverage::Miss => {
                    if let Coverage::Ignore = a {
                        a = Coverage::Miss
                    }
                }
                Coverage::Partial(f) => {
                    if f.to_f64().unwrap() > a.get_value() {
                        a = Coverage::Partial(*f);
                    }
                }
                Coverage::Ignore => {}
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
        assert_eq!(Coverage::join_coverages(vec![]), Coverage::Ignore);
        assert_eq!(
            Coverage::join_coverages(vec![&Coverage::Ignore, &Coverage::Miss]),
            Coverage::Miss
        );
        assert_eq!(
            Coverage::join_coverages(vec![&Coverage::Ignore, &Coverage::Ignore]),
            Coverage::Ignore
        );
        assert_eq!(
            Coverage::join_coverages(vec![&Coverage::Miss, &Coverage::Ignore]),
            Coverage::Miss
        );
        assert_eq!(
            Coverage::join_coverages(vec![&Coverage::Miss, &Coverage::Ignore, &Coverage::Hit]),
            Coverage::Hit
        );
    }
}
