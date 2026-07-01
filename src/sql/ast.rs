use crate::ValueType;

#[derive(Debug, Clone, PartialEq)]
pub enum Statement {
    CreateTable {
        name: String,
        columns: Vec<ColumnDef>,
    },
    Insert {
        table: String,
        values: Vec<Literal>,
    },
    Select {
        table: String,
        projection: SelectProjection,
        limit: Option<usize>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ColumnDef {
    name: String,
    value_type: ValueType,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Literal {
    Null,
    Integer(i64),
    Real(f64),
    Text(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SelectProjection {
    All,
    Columns(Vec<String>),
}

impl ColumnDef {
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
