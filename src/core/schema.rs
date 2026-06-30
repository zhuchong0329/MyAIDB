use std::collections::HashSet;

use super::{Row, ValueType};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Column {
    name: String,
    value_type: ValueType,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Schema {
    columns: Vec<Column>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SchemaError {
    ColumnCountMismatch {
        expected: usize,
        actual: usize,
    },
    TypeMismatch {
        column_index: usize,
        column_name: String,
        expected: ValueType,
        actual: ValueType,
    },
    DuplicateColumn {
        name: String,
    },
    ColumnNotFound {
        name: String,
    },
}

impl Column {
    pub fn new(name: impl Into<String>, value_type: ValueType) -> Self {
        Self {
            name: name.into(),
            value_type,
        }
    }

    pub fn name(&self) -> &str {
        self.name.as_str()
    }

    pub fn value_type(&self) -> ValueType {
        self.value_type
    }
}

impl Schema {
    pub fn new(columns: impl Into<Vec<Column>>) -> Result<Self, SchemaError> {
        let columns = columns.into();
        let mut names = HashSet::with_capacity(columns.len());

        for column in &columns {
            if !names.insert(column.name()) {
                return Err(SchemaError::DuplicateColumn {
                    name: column.name().to_string(),
                });
            }
        }

        Ok(Self { columns })
    }

    pub fn len(&self) -> usize {
        self.columns.len()
    }

    pub fn is_empty(&self) -> bool {
        self.columns.is_empty()
    }

    pub fn column(&self, index: usize) -> Option<&Column> {
        self.columns.get(index)
    }

    pub fn columns(&self) -> &[Column] {
        self.columns.as_slice()
    }

    pub fn column_index(&self, name: &str) -> Result<usize, SchemaError> {
        self.columns
            .iter()
            .position(|column| column.name() == name)
            .ok_or_else(|| SchemaError::ColumnNotFound {
                name: name.to_string(),
            })
    }

    pub fn validate_row(&self, row: &Row) -> Result<(), SchemaError> {
        if row.len() != self.len() {
            return Err(SchemaError::ColumnCountMismatch {
                expected: self.len(),
                actual: row.len(),
            });
        }

        for (index, (column, value)) in self.columns.iter().zip(row.values()).enumerate() {
            let actual = value.value_type();
            let expected = column.value_type();

            if actual != expected {
                return Err(SchemaError::TypeMismatch {
                    column_index: index,
                    column_name: column.name().to_string(),
                    expected,
                    actual,
                });
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Value, ValueType};

    fn user_schema() -> Schema {
        Schema::new(vec![
            Column::new("id", ValueType::Integer),
            Column::new("name", ValueType::Text),
            Column::new("embedding", ValueType::Vector),
        ])
        .expect("schema should be valid")
    }

    #[test]
    fn schema_owns_columns_and_supports_indexed_access() {
        let schema = user_schema();

        assert_eq!(schema.len(), 3);
        assert!(!schema.is_empty());
        assert_eq!(schema.column(0).map(Column::name), Some("id"));
        assert_eq!(
            schema.column(1).map(Column::value_type),
            Some(ValueType::Text)
        );
        assert_eq!(schema.column(3), None);
    }

    #[test]
    fn schema_supports_exact_column_name_lookup() {
        let schema = user_schema();

        assert_eq!(schema.column_index("id"), Ok(0));
        assert_eq!(schema.column_index("name"), Ok(1));
        assert_eq!(
            schema.column_index("Name"),
            Err(SchemaError::ColumnNotFound {
                name: String::from("Name"),
            })
        );
    }

    #[test]
    fn schema_rejects_duplicate_column_names() {
        let result = Schema::new(vec![
            Column::new("id", ValueType::Integer),
            Column::new("id", ValueType::Text),
        ]);

        assert_eq!(
            result,
            Err(SchemaError::DuplicateColumn {
                name: String::from("id"),
            })
        );
    }

    #[test]
    fn schema_validates_matching_row_shape() {
        let schema = user_schema();
        let row = Row::new(vec![
            Value::integer(1),
            Value::text("Ada"),
            Value::vector(vec![0.1, 0.2]),
        ]);

        assert_eq!(schema.validate_row(&row), Ok(()));
    }

    #[test]
    fn schema_rejects_row_length_mismatch() {
        let schema = user_schema();
        let row = Row::new(vec![Value::integer(1), Value::text("Ada")]);

        assert_eq!(
            schema.validate_row(&row),
            Err(SchemaError::ColumnCountMismatch {
                expected: 3,
                actual: 2,
            })
        );
    }

    #[test]
    fn schema_rejects_value_type_mismatch() {
        let schema = user_schema();
        let row = Row::new(vec![
            Value::integer(1),
            Value::integer(99),
            Value::vector(vec![0.1, 0.2]),
        ]);

        assert_eq!(
            schema.validate_row(&row),
            Err(SchemaError::TypeMismatch {
                column_index: 1,
                column_name: String::from("name"),
                expected: ValueType::Text,
                actual: ValueType::Integer,
            })
        );
    }

    #[test]
    fn null_matches_only_null_columns() {
        let nullable_schema = Schema::new(vec![Column::new("deleted_at", ValueType::Null)])
            .expect("schema should be valid");
        let text_schema = Schema::new(vec![Column::new("title", ValueType::Text)])
            .expect("schema should be valid");

        assert_eq!(
            nullable_schema.validate_row(&Row::new(vec![Value::null()])),
            Ok(())
        );
        assert_eq!(
            text_schema.validate_row(&Row::new(vec![Value::null()])),
            Err(SchemaError::TypeMismatch {
                column_index: 0,
                column_name: String::from("title"),
                expected: ValueType::Text,
                actual: ValueType::Null,
            })
        );
    }
}
