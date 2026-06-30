use super::{Schema, Table};

#[derive(Debug, Clone, PartialEq)]
pub struct Catalog {
    tables: Vec<Table>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CatalogError {
    DuplicateTable { name: String },
    TableNotFound { name: String },
}

impl Catalog {
    pub fn new() -> Self {
        Self { tables: Vec::new() }
    }

    pub fn len(&self) -> usize {
        self.tables.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tables.is_empty()
    }

    pub fn create_table(
        &mut self,
        name: impl Into<String>,
        schema: Schema,
    ) -> Result<(), CatalogError> {
        self.insert_table(Table::new(name, schema))
    }

    pub fn insert_table(&mut self, table: Table) -> Result<(), CatalogError> {
        if self.contains_table(table.name()) {
            return Err(CatalogError::DuplicateTable {
                name: table.name().to_string(),
            });
        }

        self.tables.push(table);
        Ok(())
    }

    pub fn table(&self, name: &str) -> Result<&Table, CatalogError> {
        self.tables
            .iter()
            .find(|table| table.name() == name)
            .ok_or_else(|| CatalogError::TableNotFound {
                name: name.to_string(),
            })
    }

    pub fn table_mut(&mut self, name: &str) -> Result<&mut Table, CatalogError> {
        let index = self
            .tables
            .iter()
            .position(|table| table.name() == name)
            .ok_or_else(|| CatalogError::TableNotFound {
                name: name.to_string(),
            })?;

        Ok(&mut self.tables[index])
    }

    pub fn table_names(&self) -> impl Iterator<Item = &str> {
        self.tables.iter().map(Table::name)
    }

    fn contains_table(&self, name: &str) -> bool {
        self.tables.iter().any(|table| table.name() == name)
    }
}

impl Default for Catalog {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Column, Row, Value, ValueType};

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
    fn catalog_starts_empty() {
        let catalog = Catalog::new();

        assert_eq!(catalog.len(), 0);
        assert!(catalog.is_empty());
        assert_eq!(
            catalog.table_names().collect::<Vec<_>>(),
            Vec::<&str>::new()
        );
    }

    #[test]
    fn catalog_creates_and_finds_table() {
        let mut catalog = Catalog::new();

        assert_eq!(catalog.create_table("users", user_schema()), Ok(()));

        let table = catalog.table("users").expect("table should exist");
        assert_eq!(table.name(), "users");
        assert_eq!(table.schema().len(), 2);
        assert_eq!(catalog.len(), 1);
        assert!(!catalog.is_empty());
    }

    #[test]
    fn catalog_inserts_existing_table_value() {
        let mut catalog = Catalog::new();
        let table = Table::new("users", user_schema());

        assert_eq!(catalog.insert_table(table), Ok(()));
        assert_eq!(catalog.table("users").map(Table::name), Ok("users"));
    }

    #[test]
    fn catalog_rejects_duplicate_table_names() {
        let mut catalog = Catalog::new();

        catalog
            .create_table("users", user_schema())
            .expect("first create should work");

        assert_eq!(
            catalog.create_table("users", user_schema()),
            Err(CatalogError::DuplicateTable {
                name: String::from("users"),
            })
        );
        assert_eq!(catalog.len(), 1);
    }

    #[test]
    fn catalog_reports_missing_tables() {
        let catalog = Catalog::new();

        assert_eq!(
            catalog.table("missing"),
            Err(CatalogError::TableNotFound {
                name: String::from("missing"),
            })
        );
    }

    #[test]
    fn catalog_mutable_lookup_allows_table_insert() {
        let mut catalog = Catalog::new();

        catalog
            .create_table("users", user_schema())
            .expect("create should work");

        catalog
            .table_mut("users")
            .expect("table should exist")
            .insert(user_row(1, "Ada"))
            .expect("insert should work");

        let users = catalog.table("users").expect("table should exist");
        assert_eq!(users.len(), 1);
        assert_eq!(users.row(0), Some(&user_row(1, "Ada")));
    }

    #[test]
    fn catalog_uses_exact_case_sensitive_table_names() {
        let mut catalog = Catalog::new();

        catalog
            .create_table("users", user_schema())
            .expect("create should work");
        catalog
            .create_table("Users", user_schema())
            .expect("case-distinct create should work");

        assert_eq!(catalog.len(), 2);
        assert_eq!(
            catalog.table_names().collect::<Vec<_>>(),
            vec!["users", "Users"]
        );
        assert_eq!(
            catalog.table("USERS"),
            Err(CatalogError::TableNotFound {
                name: String::from("USERS"),
            })
        );
    }
}
