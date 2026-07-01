use super::{Token, TokenKind};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LexError {
    UnexpectedCharacter { character: char, position: usize },
    UnterminatedString { position: usize },
    InvalidNumber { lexeme: String, position: usize },
}

pub fn lex(input: &str) -> Result<Vec<Token>, LexError> {
    Lexer::new(input).lex()
}

struct Lexer<'a> {
    input: &'a str,
    chars: Vec<char>,
    current: usize,
}

impl<'a> Lexer<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            input,
            chars: input.chars().collect(),
            current: 0,
        }
    }

    fn lex(mut self) -> Result<Vec<Token>, LexError> {
        let mut tokens = Vec::new();

        while let Some(character) = self.peek() {
            match character {
                ' ' | '\t' | '\r' | '\n' => {
                    self.advance();
                }
                ',' => {
                    self.advance();
                    tokens.push(Token::new(TokenKind::Comma, ","));
                }
                '=' => {
                    self.advance();
                    tokens.push(Token::new(TokenKind::Equal, "="));
                }
                '!' => {
                    let position = self.current;
                    self.advance();
                    if self.peek() != Some('=') {
                        return Err(LexError::UnexpectedCharacter {
                            character,
                            position,
                        });
                    }
                    self.advance();
                    tokens.push(Token::new(TokenKind::BangEqual, "!="));
                }
                '<' => {
                    self.advance();
                    if self.peek() == Some('=') {
                        self.advance();
                        tokens.push(Token::new(TokenKind::LessEqual, "<="));
                    } else {
                        tokens.push(Token::new(TokenKind::Less, "<"));
                    }
                }
                '>' => {
                    self.advance();
                    if self.peek() == Some('=') {
                        self.advance();
                        tokens.push(Token::new(TokenKind::GreaterEqual, ">="));
                    } else {
                        tokens.push(Token::new(TokenKind::Greater, ">"));
                    }
                }
                '*' => {
                    self.advance();
                    tokens.push(Token::new(TokenKind::Asterisk, "*"));
                }
                '(' => {
                    self.advance();
                    tokens.push(Token::new(TokenKind::LeftParen, "("));
                }
                ')' => {
                    self.advance();
                    tokens.push(Token::new(TokenKind::RightParen, ")"));
                }
                ';' => {
                    self.advance();
                    tokens.push(Token::new(TokenKind::Semicolon, ";"));
                }
                '\'' => tokens.push(self.string()?),
                character if is_identifier_start(character) => tokens.push(self.identifier()),
                character if character.is_ascii_digit() => tokens.push(self.number()?),
                character => {
                    return Err(LexError::UnexpectedCharacter {
                        character,
                        position: self.current,
                    });
                }
            }
        }

        Ok(tokens)
    }

    fn identifier(&mut self) -> Token {
        let start = self.current;

        while self.peek().is_some_and(is_identifier_continue) {
            self.advance();
        }

        Token::new(TokenKind::Identifier, self.slice(start, self.current))
    }

    fn number(&mut self) -> Result<Token, LexError> {
        let start = self.current;

        while self
            .peek()
            .is_some_and(|character| character.is_ascii_digit())
        {
            self.advance();
        }

        let mut kind = TokenKind::Integer;

        if self.peek() == Some('.')
            && self
                .peek_next()
                .is_some_and(|character| character.is_ascii_digit())
        {
            kind = TokenKind::Real;
            self.advance();

            while self
                .peek()
                .is_some_and(|character| character.is_ascii_digit())
            {
                self.advance();
            }
        }

        let lexeme = self.slice(start, self.current);
        match kind {
            TokenKind::Integer if lexeme.parse::<i64>().is_err() => Err(LexError::InvalidNumber {
                lexeme,
                position: start,
            }),
            TokenKind::Real if lexeme.parse::<f64>().is_err() => Err(LexError::InvalidNumber {
                lexeme,
                position: start,
            }),
            _ => Ok(Token::new(kind, lexeme)),
        }
    }

    fn string(&mut self) -> Result<Token, LexError> {
        let quote_position = self.current;
        self.advance();
        let start = self.current;

        while let Some(character) = self.peek() {
            if character == '\'' {
                let value = self.slice(start, self.current);
                self.advance();
                return Ok(Token::new(TokenKind::String, value));
            }

            self.advance();
        }

        Err(LexError::UnterminatedString {
            position: quote_position,
        })
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.current).copied()
    }

    fn peek_next(&self) -> Option<char> {
        self.chars.get(self.current + 1).copied()
    }

    fn advance(&mut self) {
        self.current += 1;
    }

    fn slice(&self, start: usize, end: usize) -> String {
        self.input.chars().skip(start).take(end - start).collect()
    }
}

fn is_identifier_start(character: char) -> bool {
    character.is_ascii_alphabetic() || character == '_'
}

fn is_identifier_continue(character: char) -> bool {
    is_identifier_start(character) || character.is_ascii_digit()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lexes_create_table_tokens() {
        let tokens = lex("CREATE TABLE users (id integer, name text);").expect("lex should work");

        let kinds = tokens.iter().map(Token::kind).collect::<Vec<_>>();
        assert_eq!(
            kinds,
            vec![
                TokenKind::Identifier,
                TokenKind::Identifier,
                TokenKind::Identifier,
                TokenKind::LeftParen,
                TokenKind::Identifier,
                TokenKind::Identifier,
                TokenKind::Comma,
                TokenKind::Identifier,
                TokenKind::Identifier,
                TokenKind::RightParen,
                TokenKind::Semicolon,
            ]
        );
        assert!(tokens[0].is_keyword("create"));
        assert_eq!(tokens[2].lexeme(), "users");
    }

    #[test]
    fn lexes_insert_literals() {
        let tokens =
            lex("insert into Users values (1, 2.5, 'Ada', null)").expect("lex should work");

        assert!(tokens[0].is_keyword("INSERT"));
        assert_eq!(tokens[2].lexeme(), "Users");
        assert_eq!(tokens[5].kind(), TokenKind::Integer);
        assert_eq!(tokens[7].kind(), TokenKind::Real);
        assert_eq!(tokens[9], Token::new(TokenKind::String, "Ada"));
        assert!(tokens[11].is_keyword("NULL"));
    }

    #[test]
    fn lexes_select_asterisk() {
        let tokens = lex("select * from users limit 10").expect("lex should work");

        assert!(tokens[0].is_keyword("SELECT"));
        assert_eq!(tokens[1], Token::new(TokenKind::Asterisk, "*"));
        assert!(tokens[2].is_keyword("FROM"));
        assert_eq!(tokens[3].lexeme(), "users");
        assert!(tokens[4].is_keyword("LIMIT"));
        assert_eq!(tokens[5], Token::new(TokenKind::Integer, "10"));
    }

    #[test]
    fn lexes_comparison_operators() {
        let tokens =
            lex("select * from users where id >= 2 and name != 'Ada'").expect("lex should work");

        assert_eq!(tokens[6], Token::new(TokenKind::GreaterEqual, ">="));
        assert_eq!(tokens[10], Token::new(TokenKind::BangEqual, "!="));
        assert_eq!(
            lex("a = 1").expect("lex should work")[1].kind(),
            TokenKind::Equal
        );
        assert_eq!(
            lex("a < 1").expect("lex should work")[1].kind(),
            TokenKind::Less
        );
        assert_eq!(
            lex("a <= 1").expect("lex should work")[1].kind(),
            TokenKind::LessEqual
        );
        assert_eq!(
            lex("a > 1").expect("lex should work")[1].kind(),
            TokenKind::Greater
        );
        assert_eq!(
            lex("a >= 1").expect("lex should work")[1].kind(),
            TokenKind::GreaterEqual
        );
    }

    #[test]
    fn rejects_unexpected_characters() {
        assert_eq!(
            lex("select @"),
            Err(LexError::UnexpectedCharacter {
                character: '@',
                position: 7,
            })
        );
    }

    #[test]
    fn rejects_unterminated_strings() {
        assert_eq!(
            lex("insert into users values ('Ada)"),
            Err(LexError::UnterminatedString { position: 26 })
        );
    }
}
