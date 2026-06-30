use super::{Row, Schema, SchemaError};

#[derive(Debug, Clone, PartialEq)]
pub struct Table {
    name: String,
    schema: Schema,
    rows: Vec<Row>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TableError {
    InvalidRow(SchemaError),
}

impl Table {
    pub fn new(name: impl Into<String>, schema: Schema) -> Self {
        Self {
            name: name.into(),
            schema,
            rows: Vec::new(),
        }
    }

    pub fn name(&self) -> &str {
        self.name.as_str()
    }

    pub fn schema(&self) -> &Schema {
        &self.schema
    }

    pub fn len(&self) -> usize {
        self.rows.len()
    }

    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn row(&self, index: usize) -> Option<&Row> {
        self.rows.get(index)
    }

    pub fn rows(&self) -> &[Row] {
        self.rows.as_slice()
    }

    pub fn insert(&mut self, row: Row) -> Result<(), TableError> {
        self.schema
            .validate_row(&row)
            .map_err(TableError::InvalidRow)?;

        self.rows.push(row);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Column, Value, ValueType};

    fn user_schema() -> Schema {
        Schema::new(vec![
            Column::new("id", ValueType::Integer),
            Column::new("name", ValueType::Text),
        ])
        .expect("schema should be valid")
    }

    fn user_row(id: i64, name: &str) -> Row {
        Row::new(vec![Value::integer(id), Value::text(name)])
    }

    #[test]
    fn table_starts_empty_with_name_and_schema() {
        let schema = user_schema();
        let table = Table::new("users", schema.clone());

        assert_eq!(table.name(), "users");
        assert_eq!(table.schema(), &schema);
        assert_eq!(table.len(), 0);
        assert!(table.is_empty());
        assert_eq!(table.rows(), &[]);
        assert_eq!(table.row(0), None);
    }

    #[test]
    fn insert_accepts_valid_owned_row() {
        let mut table = Table::new("users", user_schema());
        let row = user_row(1, "Ada");

        assert_eq!(table.insert(row), Ok(()));
        assert_eq!(table.len(), 1);
        assert!(!table.is_empty());
        assert_eq!(table.row(0), Some(&user_row(1, "Ada")));
    }

    #[test]
    fn insert_rejects_row_length_mismatch_without_mutating_table() {
        let mut table = Table::new("users", user_schema());
        let invalid_row = Row::new(vec![Value::integer(1)]);

        assert_eq!(
            table.insert(invalid_row),
            Err(TableError::InvalidRow(SchemaError::ColumnCountMismatch {
                expected: 2,
                actual: 1,
            }))
        );
        assert!(table.is_empty());
    }

    #[test]
    fn insert_rejects_type_mismatch_without_mutating_table() {
        let mut table = Table::new("users", user_schema());
        let invalid_row = Row::new(vec![Value::integer(1), Value::integer(99)]);

        assert_eq!(
            table.insert(invalid_row),
            Err(TableError::InvalidRow(SchemaError::TypeMismatch {
                column_index: 1,
                column_name: String::from("name"),
                expected: ValueType::Text,
                actual: ValueType::Integer,
            }))
        );
        assert!(table.is_empty());
    }

    #[test]
    fn insert_preserves_row_order() {
        let mut table = Table::new("users", user_schema());

        table
            .insert(user_row(1, "Ada"))
            .expect("first insert should work");
        table
            .insert(user_row(2, "Grace"))
            .expect("second insert should work");

        assert_eq!(table.len(), 2);
        assert_eq!(table.row(0), Some(&user_row(1, "Ada")));
        assert_eq!(table.row(1), Some(&user_row(2, "Grace")));
        assert_eq!(table.row(2), None);
        assert_eq!(table.rows(), &[user_row(1, "Ada"), user_row(2, "Grace")]);
    }

    #[test]
    fn invalid_insert_does_not_remove_existing_rows() {
        let mut table = Table::new("users", user_schema());

        table
            .insert(user_row(1, "Ada"))
            .expect("valid insert should work");
        let result = table.insert(Row::new(vec![Value::integer(2)]));

        assert!(result.is_err());
        assert_eq!(table.rows(), &[user_row(1, "Ada")]);
    }
}
