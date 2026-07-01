use crate::ValueType;

use super::lexer::LexError;
use super::{
    lex, ColumnDef, ComparisonOperator, Literal, SelectOrder, SelectPredicate, SelectProjection,
    SortDirection, Statement, Token, TokenKind,
};

#[derive(Debug, Clone, PartialEq)]
pub enum ParseError {
    Lex(LexError),
    ExpectedKeyword {
        expected: &'static str,
        found: Option<Token>,
    },
    ExpectedToken {
        expected: TokenKind,
        found: Option<Token>,
    },
    ExpectedIdentifier {
        found: Option<Token>,
    },
    ExpectedType {
        found: Option<Token>,
    },
    ExpectedLiteral {
        found: Option<Token>,
    },
    ExpectedComparisonOperator {
        found: Option<Token>,
    },
    InvalidInteger {
        lexeme: String,
    },
    InvalidReal {
        lexeme: String,
    },
    UnexpectedToken {
        found: Token,
    },
}

impl From<LexError> for ParseError {
    fn from(error: LexError) -> Self {
        Self::Lex(error)
    }
}

pub fn parse_statement(input: &str) -> Result<Statement, ParseError> {
    let tokens = lex(input)?;
    Parser::new(tokens).parse_statement()
}

struct Parser {
    tokens: Vec<Token>,
    current: usize,
}

impl Parser {
    fn new(tokens: Vec<Token>) -> Self {
        Self { tokens, current: 0 }
    }

    fn parse_statement(&mut self) -> Result<Statement, ParseError> {
        let statement = if self.check_keyword("create") {
            self.parse_create_table()?
        } else if self.check_keyword("insert") {
            self.parse_insert()?
        } else if self.check_keyword("select") {
            self.parse_select()?
        } else {
            return Err(ParseError::ExpectedKeyword {
                expected: "CREATE, INSERT, or SELECT",
                found: self.peek().cloned(),
            });
        };

        self.match_kind(TokenKind::Semicolon);

        if let Some(token) = self.peek() {
            return Err(ParseError::UnexpectedToken {
                found: token.clone(),
            });
        }

        Ok(statement)
    }

    fn parse_create_table(&mut self) -> Result<Statement, ParseError> {
        self.consume_keyword("create")?;
        self.consume_keyword("table")?;
        let name = self.consume_identifier()?;
        self.consume_kind(TokenKind::LeftParen)?;

        let mut columns = Vec::new();

        loop {
            let column_name = self.consume_identifier()?;
            let value_type = self.consume_type()?;
            columns.push(ColumnDef::new(column_name, value_type));

            if !self.match_kind(TokenKind::Comma) {
                break;
            }
        }

        self.consume_kind(TokenKind::RightParen)?;

        Ok(Statement::CreateTable { name, columns })
    }

    fn parse_insert(&mut self) -> Result<Statement, ParseError> {
        self.consume_keyword("insert")?;
        self.consume_keyword("into")?;
        let table = self.consume_identifier()?;
        self.consume_keyword("values")?;
        self.consume_kind(TokenKind::LeftParen)?;

        let mut values = Vec::new();

        loop {
            values.push(self.consume_literal()?);

            if !self.match_kind(TokenKind::Comma) {
                break;
            }
        }

        self.consume_kind(TokenKind::RightParen)?;

        Ok(Statement::Insert { table, values })
    }

    fn parse_select(&mut self) -> Result<Statement, ParseError> {
        self.consume_keyword("select")?;
        let projection = self.consume_select_projection()?;
        self.consume_keyword("from")?;
        let table = self.consume_identifier()?;
        let filter = if self.match_keyword("where") {
            Some(self.consume_select_predicate()?)
        } else {
            None
        };
        let order = if self.match_keyword("order") {
            self.consume_keyword("by")?;
            Some(self.consume_select_order()?)
        } else {
            None
        };
        let limit = if self.match_keyword("limit") {
            Some(self.consume_limit()?)
        } else {
            None
        };

        Ok(Statement::Select {
            table,
            projection,
            filter,
            order,
            limit,
        })
    }

    fn consume_select_projection(&mut self) -> Result<SelectProjection, ParseError> {
        if self.match_kind(TokenKind::Asterisk) {
            return Ok(SelectProjection::All);
        }

        let mut columns = vec![self.consume_identifier()?];

        while self.match_kind(TokenKind::Comma) {
            columns.push(self.consume_identifier()?);
        }

        Ok(SelectProjection::Columns(columns))
    }

    fn consume_select_predicate(&mut self) -> Result<SelectPredicate, ParseError> {
        let column = self.consume_identifier()?;
        let operator = self.consume_comparison_operator()?;
        let literal = self.consume_literal()?;

        Ok(SelectPredicate::new(column, operator, literal))
    }

    fn consume_comparison_operator(&mut self) -> Result<ComparisonOperator, ParseError> {
        let token = self
            .peek()
            .cloned()
            .ok_or(ParseError::ExpectedComparisonOperator { found: None })?;

        let operator = match token.kind() {
            TokenKind::Equal => ComparisonOperator::Equal,
            TokenKind::BangEqual => ComparisonOperator::NotEqual,
            TokenKind::Less => ComparisonOperator::Less,
            TokenKind::LessEqual => ComparisonOperator::LessEqual,
            TokenKind::Greater => ComparisonOperator::Greater,
            TokenKind::GreaterEqual => ComparisonOperator::GreaterEqual,
            _ => {
                return Err(ParseError::ExpectedComparisonOperator { found: Some(token) });
            }
        };

        self.advance();
        Ok(operator)
    }

    fn consume_select_order(&mut self) -> Result<SelectOrder, ParseError> {
        let column = self.consume_identifier()?;
        let direction = if self.match_keyword("desc") {
            SortDirection::Desc
        } else {
            self.match_keyword("asc");
            SortDirection::Asc
        };

        Ok(SelectOrder::new(column, direction))
    }

    fn consume_limit(&mut self) -> Result<usize, ParseError> {
        let token = self.peek().cloned().ok_or(ParseError::ExpectedToken {
            expected: TokenKind::Integer,
            found: None,
        })?;

        if token.kind() != TokenKind::Integer {
            return Err(ParseError::ExpectedToken {
                expected: TokenKind::Integer,
                found: Some(token),
            });
        }

        let limit = token
            .lexeme()
            .parse::<usize>()
            .map_err(|_| ParseError::InvalidInteger {
                lexeme: token.lexeme().to_string(),
            })?;
        self.advance();
        Ok(limit)
    }

    fn consume_type(&mut self) -> Result<ValueType, ParseError> {
        let token = self
            .peek()
            .cloned()
            .ok_or(ParseError::ExpectedType { found: None })?;

        let value_type = if token.is_keyword("null") {
            ValueType::Null
        } else if token.is_keyword("integer") {
            ValueType::Integer
        } else if token.is_keyword("real") {
            ValueType::Real
        } else if token.is_keyword("text") {
            ValueType::Text
        } else if token.is_keyword("blob") {
            ValueType::Blob
        } else if token.is_keyword("vector") {
            ValueType::Vector
        } else {
            return Err(ParseError::ExpectedType { found: Some(token) });
        };

        self.advance();
        Ok(value_type)
    }

    fn consume_literal(&mut self) -> Result<Literal, ParseError> {
        let token = self
            .peek()
            .cloned()
            .ok_or(ParseError::ExpectedLiteral { found: None })?;

        let literal = match token.kind() {
            TokenKind::Integer => {
                Literal::Integer(token.lexeme().parse::<i64>().map_err(|_| {
                    ParseError::InvalidInteger {
                        lexeme: token.lexeme().to_string(),
                    }
                })?)
            }
            TokenKind::Real => Literal::Real(token.lexeme().parse::<f64>().map_err(|_| {
                ParseError::InvalidReal {
                    lexeme: token.lexeme().to_string(),
                }
            })?),
            TokenKind::String => Literal::Text(token.lexeme().to_string()),
            TokenKind::Identifier if token.is_keyword("null") => Literal::Null,
            _ => return Err(ParseError::ExpectedLiteral { found: Some(token) }),
        };

        self.advance();
        Ok(literal)
    }

    fn consume_identifier(&mut self) -> Result<String, ParseError> {
        let token = self
            .peek()
            .cloned()
            .ok_or(ParseError::ExpectedIdentifier { found: None })?;

        if token.kind() != TokenKind::Identifier {
            return Err(ParseError::ExpectedIdentifier { found: Some(token) });
        }

        self.advance();
        Ok(token.lexeme().to_string())
    }

    fn consume_keyword(&mut self, keyword: &'static str) -> Result<(), ParseError> {
        if self.check_keyword(keyword) {
            self.advance();
            return Ok(());
        }

        Err(ParseError::ExpectedKeyword {
            expected: keyword,
            found: self.peek().cloned(),
        })
    }

    fn consume_kind(&mut self, kind: TokenKind) -> Result<(), ParseError> {
        if self.check_kind(kind) {
            self.advance();
            return Ok(());
        }

        Err(ParseError::ExpectedToken {
            expected: kind,
            found: self.peek().cloned(),
        })
    }

    fn match_kind(&mut self, kind: TokenKind) -> bool {
        if self.check_kind(kind) {
            self.advance();
            true
        } else {
            false
        }
    }

    fn match_keyword(&mut self, keyword: &str) -> bool {
        if self.check_keyword(keyword) {
            self.advance();
            true
        } else {
            false
        }
    }

    fn check_kind(&self, kind: TokenKind) -> bool {
        self.peek().is_some_and(|token| token.kind() == kind)
    }

    fn check_keyword(&self, keyword: &str) -> bool {
        self.peek().is_some_and(|token| token.is_keyword(keyword))
    }

    fn peek(&self) -> Option<&Token> {
        self.tokens.get(self.current)
    }

    fn advance(&mut self) {
        self.current += 1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_create_table_statement() {
        let statement = parse_statement("CREATE TABLE users (id integer, name text);")
            .expect("parse should work");

        assert_eq!(
            statement,
            Statement::CreateTable {
                name: String::from("users"),
                columns: vec![
                    ColumnDef::new("id", ValueType::Integer),
                    ColumnDef::new("name", ValueType::Text),
                ],
            }
        );
    }

    #[test]
    fn parses_insert_statement() {
        let statement = parse_statement("insert into Users values (1, 2.5, 'Ada', null)")
            .expect("parse should work");

        assert_eq!(
            statement,
            Statement::Insert {
                table: String::from("Users"),
                values: vec![
                    Literal::Integer(1),
                    Literal::Real(2.5),
                    Literal::Text(String::from("Ada")),
                    Literal::Null,
                ],
            }
        );
    }

    #[test]
    fn parses_select_all_statement() {
        let statement = parse_statement("select * from Users").expect("parse should work");

        assert_eq!(
            statement,
            Statement::Select {
                table: String::from("Users"),
                projection: SelectProjection::All,
                filter: None,
                order: None,
                limit: None,
            }
        );
    }

    #[test]
    fn parses_select_projection_with_limit() {
        let statement =
            parse_statement("select name, id from users limit 10").expect("parse should work");

        assert_eq!(
            statement,
            Statement::Select {
                table: String::from("users"),
                projection: SelectProjection::Columns(vec![
                    String::from("name"),
                    String::from("id"),
                ]),
                filter: None,
                order: None,
                limit: Some(10),
            }
        );
    }

    #[test]
    fn parses_select_with_where_order_and_limit() {
        let statement =
            parse_statement("select name from users where age >= 18 order by name desc limit 10")
                .expect("parse should work");

        assert_eq!(
            statement,
            Statement::Select {
                table: String::from("users"),
                projection: SelectProjection::Columns(vec![String::from("name")]),
                filter: Some(SelectPredicate::new(
                    "age",
                    ComparisonOperator::GreaterEqual,
                    Literal::Integer(18),
                )),
                order: Some(SelectOrder::new("name", SortDirection::Desc)),
                limit: Some(10),
            }
        );
    }

    #[test]
    fn parses_select_order_by_defaulting_to_ascending() {
        let statement =
            parse_statement("select * from users order by name").expect("parse should work");

        assert_eq!(
            statement,
            Statement::Select {
                table: String::from("users"),
                projection: SelectProjection::All,
                filter: None,
                order: Some(SelectOrder::new("name", SortDirection::Asc)),
                limit: None,
            }
        );
    }

    #[test]
    fn parses_all_supported_create_table_types() {
        let statement = parse_statement(
            "create table values_table (a null, b integer, c real, d text, e blob, f vector)",
        )
        .expect("parse should work");

        assert_eq!(
            statement,
            Statement::CreateTable {
                name: String::from("values_table"),
                columns: vec![
                    ColumnDef::new("a", ValueType::Null),
                    ColumnDef::new("b", ValueType::Integer),
                    ColumnDef::new("c", ValueType::Real),
                    ColumnDef::new("d", ValueType::Text),
                    ColumnDef::new("e", ValueType::Blob),
                    ColumnDef::new("f", ValueType::Vector),
                ],
            }
        );
    }

    #[test]
    fn keywords_are_case_insensitive_but_identifiers_are_preserved() {
        let statement =
            parse_statement("CrEaTe TaBlE Users (UserName TeXt)").expect("parse should work");

        assert_eq!(
            statement,
            Statement::CreateTable {
                name: String::from("Users"),
                columns: vec![ColumnDef::new("UserName", ValueType::Text)],
            }
        );
    }

    #[test]
    fn semicolon_is_optional_but_extra_tokens_are_rejected() {
        let statement =
            parse_statement("create table users (id integer)").expect("parse should work");

        assert!(matches!(statement, Statement::CreateTable { .. }));
        assert_eq!(
            parse_statement("create table users (id integer); ;"),
            Err(ParseError::UnexpectedToken {
                found: Token::new(TokenKind::Semicolon, ";"),
            })
        );
    }

    #[test]
    fn select_limit_requires_integer() {
        assert_eq!(
            parse_statement("select * from users limit nope"),
            Err(ParseError::ExpectedToken {
                expected: TokenKind::Integer,
                found: Some(Token::new(TokenKind::Identifier, "nope")),
            })
        );
    }

    #[test]
    fn select_where_requires_comparison_operator() {
        assert_eq!(
            parse_statement("select * from users where id 1"),
            Err(ParseError::ExpectedComparisonOperator {
                found: Some(Token::new(TokenKind::Integer, "1")),
            })
        );
    }

    #[test]
    fn rejects_unknown_type_names() {
        assert_eq!(
            parse_statement("create table users (id uuid)"),
            Err(ParseError::ExpectedType {
                found: Some(Token::new(TokenKind::Identifier, "uuid")),
            })
        );
    }
}
