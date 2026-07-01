use crate::{Catalog, CatalogError, Column, Row, Schema, SchemaError, TableError, Value};

use super::{parse_statement, Literal, ParseError, SelectProjection, Statement};

#[derive(Debug, Clone, PartialEq)]
pub enum ExecuteResult {
    CreateTable {
        table: String,
    },
    Insert {
        table: String,
        rows_inserted: usize,
    },
    Select {
        columns: Vec<Column>,
        rows: Vec<Row>,
    },
}

#[derive(Debug, Clone, PartialEq)]
pub enum ExecuteError {
    Parse(ParseError),
    Schema(SchemaError),
    Catalog(CatalogError),
    Table(TableError),
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

impl From<TableError> for ExecuteError {
    fn from(error: TableError) -> Self {
        Self::Table(error)
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
        Statement::Insert { table, values } => {
            let row_values = values.into_iter().map(literal_to_value).collect::<Vec<_>>();
            let row = Row::new(row_values);

            catalog.table_mut(&table)?.insert(row)?;

            Ok(ExecuteResult::Insert {
                table,
                rows_inserted: 1,
            })
        }
        Statement::Select {
            table,
            projection,
            limit,
        } => execute_select(catalog, table, projection, limit),
    }
}

fn execute_select(
    catalog: &Catalog,
    table: String,
    projection: SelectProjection,
    limit: Option<usize>,
) -> Result<ExecuteResult, ExecuteError> {
    let table = catalog.table(&table)?;
    let schema = table.schema();
    let indices = match projection {
        SelectProjection::All => (0..schema.len()).collect::<Vec<_>>(),
        SelectProjection::Columns(columns) => columns
            .iter()
            .map(|column| schema.column_index(column))
            .collect::<Result<Vec<_>, _>>()?,
    };
    let columns = indices
        .iter()
        .map(|index| {
            schema
                .column(*index)
                .expect("projection index should come from schema")
                .clone()
        })
        .collect::<Vec<_>>();
    let rows = table
        .rows()
        .iter()
        .take(limit.unwrap_or(usize::MAX))
        .map(|row| project_row(row, &indices))
        .collect::<Vec<_>>();

    Ok(ExecuteResult::Select { columns, rows })
}

fn project_row(row: &Row, indices: &[usize]) -> Row {
    Row::new(
        indices
            .iter()
            .map(|index| {
                row.get(*index)
                    .expect("projection index should be valid for row")
                    .clone()
            })
            .collect::<Vec<_>>(),
    )
}

fn literal_to_value(literal: Literal) -> Value {
    match literal {
        Literal::Null => Value::null(),
        Literal::Integer(value) => Value::integer(value),
        Literal::Real(value) => Value::real(value),
        Literal::Text(value) => Value::text(value),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{LexError, Token, TokenKind, ValueType};

    fn create_users_with_rows(catalog: &mut Catalog) {
        execute_sql(catalog, "create table users (id integer, name text)")
            .expect("create should work");
        execute_sql(catalog, "insert into users values (1, 'Ada')")
            .expect("first insert should work");
        execute_sql(catalog, "insert into users values (2, 'Grace')")
            .expect("second insert should work");
    }

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
            execute_sql(&mut catalog, "create table users @"),
            Err(ExecuteError::Parse(ParseError::Lex(
                LexError::UnexpectedCharacter {
                    character: '@',
                    position: 19,
                }
            )))
        );
        assert!(catalog.is_empty());
    }

    #[test]
    fn execute_insert_appends_row_to_catalog_table() {
        let mut catalog = Catalog::new();

        execute_sql(
            &mut catalog,
            "create table users (id integer, score real, name text)",
        )
        .expect("create should work");

        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (1, 9.5, 'Ada')"),
            Ok(ExecuteResult::Insert {
                table: String::from("users"),
                rows_inserted: 1,
            })
        );

        let table = catalog.table("users").expect("table should exist");
        assert_eq!(table.len(), 1);
        assert_eq!(
            table.row(0).cloned(),
            Some(Row::new(vec![
                Value::integer(1),
                Value::real(9.5),
                Value::text("Ada"),
            ]))
        );
    }

    #[test]
    fn execute_insert_preserves_row_order() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table users (id integer, name text)")
            .expect("create should work");
        execute_sql(&mut catalog, "insert into users values (1, 'Ada')")
            .expect("first insert should work");
        execute_sql(&mut catalog, "insert into users values (2, 'Grace')")
            .expect("second insert should work");

        let table = catalog.table("users").expect("table should exist");
        assert_eq!(table.len(), 2);
        assert_eq!(
            table.row(0).cloned(),
            Some(Row::new(vec![Value::integer(1), Value::text("Ada")]))
        );
        assert_eq!(
            table.row(1).cloned(),
            Some(Row::new(vec![Value::integer(2), Value::text("Grace")]))
        );
    }

    #[test]
    fn insert_into_missing_table_surfaces_catalog_error() {
        let mut catalog = Catalog::new();

        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (1, 'Ada')"),
            Err(ExecuteError::Catalog(CatalogError::TableNotFound {
                name: String::from("users"),
            }))
        );
        assert!(catalog.is_empty());
    }

    #[test]
    fn insert_row_length_mismatch_surfaces_table_error_without_mutating_table() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table users (id integer, name text)")
            .expect("create should work");

        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (1)"),
            Err(ExecuteError::Table(TableError::InvalidRow(
                SchemaError::ColumnCountMismatch {
                    expected: 2,
                    actual: 1,
                }
            )))
        );
        assert!(catalog
            .table("users")
            .expect("table should exist")
            .is_empty());
    }

    #[test]
    fn insert_type_mismatch_surfaces_table_error_without_mutating_table() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table users (id integer, name text)")
            .expect("create should work");
        execute_sql(&mut catalog, "insert into users values (1, 'Ada')")
            .expect("valid insert should work");

        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (2, 99)"),
            Err(ExecuteError::Table(TableError::InvalidRow(
                SchemaError::TypeMismatch {
                    column_index: 1,
                    column_name: String::from("name"),
                    expected: ValueType::Text,
                    actual: ValueType::Integer,
                }
            )))
        );

        let table = catalog.table("users").expect("table should exist");
        assert_eq!(table.len(), 1);
        assert_eq!(
            table.row(0).cloned(),
            Some(Row::new(vec![Value::integer(1), Value::text("Ada")]))
        );
    }

    #[test]
    fn insert_null_uses_existing_strict_null_semantics() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table events (deleted_at null)")
            .expect("create should work");
        assert_eq!(
            execute_sql(&mut catalog, "insert into events values (null)"),
            Ok(ExecuteResult::Insert {
                table: String::from("events"),
                rows_inserted: 1,
            })
        );

        execute_sql(&mut catalog, "create table users (name text)").expect("create should work");
        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (null)"),
            Err(ExecuteError::Table(TableError::InvalidRow(
                SchemaError::TypeMismatch {
                    column_index: 0,
                    column_name: String::from("name"),
                    expected: ValueType::Text,
                    actual: ValueType::Null,
                }
            )))
        );
        assert!(catalog
            .table("users")
            .expect("table should exist")
            .is_empty());
    }

    #[test]
    fn insert_uses_exact_table_names() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table Users (id integer)").expect("create should work");

        assert_eq!(
            execute_sql(&mut catalog, "insert into users values (1)"),
            Err(ExecuteError::Catalog(CatalogError::TableNotFound {
                name: String::from("users"),
            }))
        );
        assert_eq!(
            execute_sql(&mut catalog, "insert into Users values (1)"),
            Ok(ExecuteResult::Insert {
                table: String::from("Users"),
                rows_inserted: 1,
            })
        );
        assert_eq!(catalog.table("Users").expect("table should exist").len(), 1);
    }

    #[test]
    fn execute_select_all_returns_full_rows() {
        let mut catalog = Catalog::new();
        create_users_with_rows(&mut catalog);

        assert_eq!(
            execute_sql(&mut catalog, "select * from users"),
            Ok(ExecuteResult::Select {
                columns: vec![
                    Column::new("id", ValueType::Integer),
                    Column::new("name", ValueType::Text),
                ],
                rows: vec![
                    Row::new(vec![Value::integer(1), Value::text("Ada")]),
                    Row::new(vec![Value::integer(2), Value::text("Grace")]),
                ],
            })
        );
    }

    #[test]
    fn execute_select_projection_returns_requested_columns_and_values() {
        let mut catalog = Catalog::new();
        create_users_with_rows(&mut catalog);

        assert_eq!(
            execute_sql(&mut catalog, "select name, id from users"),
            Ok(ExecuteResult::Select {
                columns: vec![
                    Column::new("name", ValueType::Text),
                    Column::new("id", ValueType::Integer),
                ],
                rows: vec![
                    Row::new(vec![Value::text("Ada"), Value::integer(1)]),
                    Row::new(vec![Value::text("Grace"), Value::integer(2)]),
                ],
            })
        );
    }

    #[test]
    fn execute_select_limit_returns_first_rows_in_insert_order() {
        let mut catalog = Catalog::new();
        create_users_with_rows(&mut catalog);

        assert_eq!(
            execute_sql(&mut catalog, "select * from users limit 1"),
            Ok(ExecuteResult::Select {
                columns: vec![
                    Column::new("id", ValueType::Integer),
                    Column::new("name", ValueType::Text),
                ],
                rows: vec![Row::new(vec![Value::integer(1), Value::text("Ada")])],
            })
        );
    }

    #[test]
    fn execute_select_missing_table_surfaces_catalog_error() {
        let mut catalog = Catalog::new();

        assert_eq!(
            execute_sql(&mut catalog, "select * from users"),
            Err(ExecuteError::Catalog(CatalogError::TableNotFound {
                name: String::from("users"),
            }))
        );
    }

    #[test]
    fn execute_select_missing_column_surfaces_schema_error() {
        let mut catalog = Catalog::new();
        create_users_with_rows(&mut catalog);

        assert_eq!(
            execute_sql(&mut catalog, "select email from users"),
            Err(ExecuteError::Schema(SchemaError::ColumnNotFound {
                name: String::from("email"),
            }))
        );
    }

    #[test]
    fn execute_select_uses_exact_table_and_column_names() {
        let mut catalog = Catalog::new();

        execute_sql(&mut catalog, "create table Users (UserName text)")
            .expect("create should work");
        execute_sql(&mut catalog, "insert into Users values ('Ada')").expect("insert should work");

        assert_eq!(
            execute_sql(&mut catalog, "select UserName from Users"),
            Ok(ExecuteResult::Select {
                columns: vec![Column::new("UserName", ValueType::Text)],
                rows: vec![Row::new(vec![Value::text("Ada")])],
            })
        );
        assert_eq!(
            execute_sql(&mut catalog, "select username from Users"),
            Err(ExecuteError::Schema(SchemaError::ColumnNotFound {
                name: String::from("username"),
            }))
        );
        assert_eq!(
            execute_sql(&mut catalog, "select UserName from users"),
            Err(ExecuteError::Catalog(CatalogError::TableNotFound {
                name: String::from("users"),
            }))
        );
    }

    #[test]
    fn execute_select_does_not_mutate_table() {
        let mut catalog = Catalog::new();
        create_users_with_rows(&mut catalog);

        execute_sql(&mut catalog, "select name from users limit 1").expect("select should work");

        let table = catalog.table("users").expect("table should exist");
        assert_eq!(table.len(), 2);
        assert_eq!(
            table.row(0).cloned(),
            Some(Row::new(vec![Value::integer(1), Value::text("Ada")]))
        );
        assert_eq!(
            table.row(1).cloned(),
            Some(Row::new(vec![Value::integer(2), Value::text("Grace")]))
        );
    }
}
