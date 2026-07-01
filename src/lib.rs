pub mod cli;
pub mod core;
pub mod sql;

pub use core::{
    Catalog, CatalogError, Column, Row, Schema, SchemaError, Table, TableError, Value, ValueType,
};
pub use sql::{
    execute_sql, parse_statement, ColumnDef, ExecuteError, ExecuteResult, LexError, Literal,
    ParseError, SelectProjection, Statement, Token, TokenKind,
};

pub const PROJECT_NAME: &str = "MyAIDB";

pub fn project_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

pub fn project_identity() -> String {
    format!("{} {}", PROJECT_NAME, project_version())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exposes_project_identity() {
        assert_eq!(PROJECT_NAME, "MyAIDB");
        assert_eq!(project_version(), "0.1.0");
        assert_eq!(project_identity(), "MyAIDB 0.1.0");
    }
}
