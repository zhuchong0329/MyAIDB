#[derive(Debug, Clone, PartialEq)]
pub struct Token {
    kind: TokenKind,
    lexeme: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TokenKind {
    Identifier,
    Integer,
    Real,
    String,
    Asterisk,
    Comma,
    LeftParen,
    RightParen,
    Semicolon,
}

impl Token {
    pub fn new(kind: TokenKind, lexeme: impl Into<String>) -> Self {
        Self {
            kind,
            lexeme: lexeme.into(),
        }
    }

    pub fn kind(&self) -> TokenKind {
        self.kind
    }

    pub fn lexeme(&self) -> &str {
        self.lexeme.as_str()
    }

    pub fn is_keyword(&self, keyword: &str) -> bool {
        self.kind == TokenKind::Identifier && self.lexeme.eq_ignore_ascii_case(keyword)
    }
}
