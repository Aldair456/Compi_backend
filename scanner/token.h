#ifndef TOKEN_H
#define TOKEN_H

#include <string>
#include <iostream>

using namespace std;

enum class TokenType {
    INT, FLOAT, LONG, UNSIGNED,
    IF, ELSE, WHILE, FOR, RETURN,
    PRINTF, INCLUDE,
    PLUS, MINUS, MULTIPLY, DIVIDE, MODULO,
    INCREMENT, DECREMENT,
    
    ASSIGN, PLUSEQ, MINUSEQ,
    
    EQ, NE, LT, GT, LE, GE,
    
    AND, OR, NOT,
    
    LPAREN, RPAREN,
    LBRACE, RBRACE,
    LBRACKET, RBRACKET,
    SEMICOLON, COMMA,
    
    INT_LITERAL,
    FLOAT_LITERAL,
    LONG_LITERAL,
    STRING_LITERAL,
    
    IDENTIFIER,
    END_OF_FILE,
    TYPEDEF,
    UNKNOWN
};

class Token {
public:
    TokenType type;
    string lexeme;
    int line;
    int column;
    
    Token(TokenType type, string lexeme, int line, int column);
    
    Token();
    
    string toString() const;
    
    static string typeToString(TokenType type);
};

#endif
