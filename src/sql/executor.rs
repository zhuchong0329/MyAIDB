use crate::{Catalog, CatalogError, Column, Schema, SchemaError};

use super::{parse_statement, ParseError, Statement};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExecuteResult {
    CreateTable { table: String },
}

#[derive(Debug, Clone, PartialEq)]
pub enum ExecuteError {
    Parse(ParseError),
    Schema(SchemaError),
    Catalog(CatalogError),
    UnsupportedStatement { statement: &'static str },
}

impl From<ParseError> for ExecuteError {
    fn from(error: ParseError) -> Self {
        Self::Parse(error)
    }
}

impl From<SchemaError> for ExecuteError {
    fn from(error: SchemaError) -> Self {
        Self::Schema(error)
    }
}

impl From<CatalogError> for ExecuteError {
    fn from(error: CatalogError) -> Self {
        Self::Catalog(error)
    }
}

pub fn execute_sql(catalog: &mut Catalog, sql: &str) -> Result<ExecuteResult, ExecuteError> {
    let statement = parse_statement(sql)?;
    execute_statement(catalog, statement)
}

fn execute_statement(
    catalog: &mut Catalog,
    statement: Statement,
) -> Result<ExecuteResult, ExecuteError> {
    match statement {
        Statement::CreateTable { name, columns } => {
            let schema_columns = columns
                .iter()
                .map(|column| Column::new(column.name(), column.value_type()))
                .collect::<Vec<_>>();
            let schema = Schema::new(schema_columns)?;

            catalog.create_table(name.clone(), schema)?;

            Ok(ExecuteResult::CreateTable { table: name })
        }
        Statement::Insert { .. } => Err(ExecuteError::UnsupportedStatement {
            statement: "INSERT",
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{LexError, Token, TokenKind, ValueType};

    #[test]
    fn execute_create_table_creates_catalog_table() {
        let mut catalog = Catalog::new();

        let result = execute_sql(
            &mut catalog,
            "CREATE TABLE users (id integer, name text, embedding vector);",
        );

        assert_eq!(
            result,
            Ok(ExecuteResult::CreateTable {
                table: String::from("users"),
            })
        );

        let table = catalog.table("users").expect("table should exist");
        assert_eq!(table.name(), "users");
        assert_eq!(table.len(), 0);
        assert_eq!(table.schema().len(), 3);
        assert_eq!(
            table.schema().column(0).map(|column| column.name()),
            Some("id")
        );
        assert_eq!(
            table.schema().column(0).map(|column| column.value_type()),
            Some(ValueType::Integer)
        );
        assert_eq!(
            table.schema().column(1).map(|column| column.name()),
            Some("name")
        );
        assert_eq!(
            table.schema().column(1).map(|column| column.value_type()),
            Some(ValueType::Text)
        );
        assert_eq!(
            table.schema().column(2).map(|column| column.name()),
            Some("embedding")
        );
        assert_eq!(
            table.schema().column(2).map(|column| column.value_type()),
            Some(ValueType::Vector)
        );
    }

    #[test]
    fn execute_create_table_preserves_exact_table_and_column_names() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "CrEaTe TaBlE Users (UserName TeXt)")
            .expect("create should work");

        assert!(catalog.table("Users").is_ok());
        assert_eq!(
            catalog
                .table("Users")
                .expect("table should exist")
                .schema()
                .column(0)
                .map(|column| column.name()),
            Some("UserName")
        );
        assert!(catalog.table("users").is_err());
    }

    #[test]
    fn duplicate_table_surfaces_catalog_error() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table users (id integer)")
            .expect("first create should work");

        assert_eq!(
            execute_sql(&mut catalog, "create table users (name text)"),
            Err(ExecuteError::Catalog(CatalogError::DuplicateTable {
                name: String::from("users"),
            }))
        );
        assert_eq!(catalog.len(), 1);
        assert_eq!(
            catalog
                .table("users")
                .expect("original table should remain")
                .schema()
                .column(0)
                .map(|column| column.name()),
            Some("id")
        );
    }

    #[test]
    fn duplicate_columns_surface_schema_error_without_mutating_catalog() {
        let mut catalog = Catalog::new();

        assert_eq!(
            execute_sql(&mut catalog, "create table users (id integer, id text)"),
            Err(ExecuteError::Schema(SchemaError::DuplicateColumn {
                name: String::from("id"),
            }))
        );
        assert!(catalog.is_empty());
        assert!(catalog.table("users").is_err());
    }

    #[test]
    fn syntax_errors_surface_parse_error_without_mutating_catalog() {
        let mut catalog = Catalog::new();

        assert_eq!(
            execute_sql(&mut catalog, "create users (id integer)"),
            Err(ExecuteError::Parse(ParseError::ExpectedKeyword {
                expected: "table",
                found: Some(Token::new(TokenKind::Identifier, "users")),
            }))
        );
        assert!(catalog.is_empty());
    }

    #[test]
    fn lexer_errors_surface_parse_error_without_mutating_catalog() {
        let mut catalog = Catalog::new();

        assert_eq!(
            execute_sql(&mut catalog, "create table users *"),
            Err(ExecuteError::Parse(ParseError::Lex(
                LexError::UnexpectedCharacter {
                    character: '*',
                    position: 19,
                }
            )))
        );
        assert!(catalog.is_empty());
    }

    #[test]
    fn insert_is_explicitly_unsupported_in_this_loop() {
        let mut catalog = Catalog::new();

        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (1, 'Ada')"),
            Err(ExecuteError::UnsupportedStatement {
                statement: "INSERT",
            })
        );
        assert!(catalog.is_empty());
    }
}
