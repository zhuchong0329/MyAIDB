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
        filter: Option<SelectPredicate>,
        order: Option<SelectOrder>,
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

#[derive(Debug, Clone, PartialEq)]
pub struct SelectPredicate {
    column: String,
    operator: ComparisonOperator,
    literal: Literal,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ComparisonOperator {
    Equal,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SelectOrder {
    column: String,
    direction: SortDirection,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortDirection {
    Asc,
    Desc,
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

impl SelectPredicate {
    pub fn new(column: impl Into<String>, operator: ComparisonOperator, literal: Literal) -> Self {
        Self {
            column: column.into(),
            operator,
            literal,
        }
    }

    pub fn column(&self) -> &str {
        self.column.as_str()
    }

    pub fn operator(&self) -> ComparisonOperator {
        self.operator
    }

    pub fn literal(&self) -> &Literal {
        &self.literal
    }
}

impl SelectOrder {
    pub fn new(column: impl Into<String>, direction: SortDirection) -> Self {
        Self {
            column: column.into(),
            direction,
        }
    }

    pub fn column(&self) -> &str {
        self.column.as_str()
    }

    pub fn direction(&self) -> SortDirection {
        self.direction
    }
}
