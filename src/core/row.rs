use super::Value;

#[derive(Debug, Clone, PartialEq)]
pub struct Row {
    values: Vec<Value>,
}

impl Row {
    pub fn new(values: impl Into<Vec<Value>>) -> Self {
        Self {
            values: values.into(),
        }
    }

    pub fn len(&self) -> usize {
        self.values.len()
    }

    pub fn is_empty(&self) -> bool {
        self.values.is_empty()
    }

    pub fn get(&self, index: usize) -> Option<&Value> {
        self.values.get(index)
    }

    pub fn values(&self) -> &[Value] {
        self.values.as_slice()
    }

    pub fn into_values(self) -> Vec<Value> {
        self.values
    }
}

impl From<Vec<Value>> for Row {
    fn from(values: Vec<Value>) -> Self {
        Self::new(values)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn row_owns_values_and_exposes_read_only_access() {
        let row = Row::new(vec![Value::integer(1), Value::text("title")]);

        assert_eq!(row.len(), 2);
        assert!(!row.is_empty());
        assert_eq!(row.get(0), Some(&Value::integer(1)));
        assert_eq!(row.get(1), Some(&Value::text("title")));
        assert_eq!(row.get(2), None);
        assert_eq!(row.values(), &[Value::integer(1), Value::text("title")]);
    }

    #[test]
    fn empty_row_is_allowed_as_a_value_container() {
        let row = Row::new(Vec::new());

        assert_eq!(row.len(), 0);
        assert!(row.is_empty());
        assert_eq!(row.values(), &[]);
    }

    #[test]
    fn row_can_return_owned_values() {
        let values = vec![Value::real(1.5), Value::null()];
        let row = Row::new(values.clone());

        assert_eq!(row.into_values(), values);
    }
}
