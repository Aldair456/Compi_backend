#include "token.h"

Token::Token(TokenType type, string lexeme, int line, int column) 
    : type(type), lexeme(lexeme), line(line), column(column) {}

Token::Token() : type(TokenType::UNKNOWN), lexeme(""), line(0), column(0) {}

string Token::toString() const {
    return "Token(" + typeToString(type) + ", \"" + lexeme + "\", " + 
           to_string(line) + ":" + to_string(column) + ")";
}

string Token::typeToString(TokenType type) {
    switch(type) {
        case TokenType::INT: return "INT";
        case TokenType::FLOAT: return "FLOAT";
        case TokenType::LONG: return "LONG";
        case TokenType::UNSIGNED: return "UNSIGNED";
        case TokenType::IF: return "IF";
        case TokenType::ELSE: return "ELSE";
        case TokenType::WHILE: return "WHILE";
        case TokenType::FOR: return "FOR";
        case TokenType::RETURN: return "RETURN";
        case TokenType::PRINTF: return "PRINTF";
        case TokenType::INCLUDE: return "INCLUDE";
        
        case TokenType::PLUS: return "PLUS";
        case TokenType::MINUS: return "MINUS";
        case TokenType::MULTIPLY: return "MULTIPLY";
        case TokenType::DIVIDE: return "DIVIDE";
        case TokenType::MODULO: return "MODULO";
        case TokenType::INCREMENT: return "INCREMENT";
        case TokenType::DECREMENT: return "DECREMENT";
        
        case TokenType::ASSIGN: return "ASSIGN";
        case TokenType::PLUSEQ: return "PLUSEQ";
        case TokenType::MINUSEQ: return "MINUSEQ";
        
        case TokenType::EQ: return "EQ";
        case TokenType::NE: return "NE";
        case TokenType::LT: return "LT";
        case TokenType::GT: return "GT";
        case TokenType::LE: return "LE";
        case TokenType::GE: return "GE";
        
        case TokenType::AND: return "AND";
        case TokenType::OR: return "OR";
        case TokenType::NOT: return "NOT";
        
        case TokenType::LPAREN: return "LPAREN";
        case TokenType::RPAREN: return "RPAREN";
        case TokenType::LBRACE: return "LBRACE";
        case TokenType::RBRACE: return "RBRACE";
        case TokenType::LBRACKET: return "LBRACKET";
        case TokenType::RBRACKET: return "RBRACKET";
        case TokenType::SEMICOLON: return "SEMICOLON";
        case TokenType::COMMA: return "COMMA";
        
        case TokenType::INT_LITERAL: return "INT_LITERAL";
        case TokenType::FLOAT_LITERAL: return "FLOAT_LITERAL";
        case TokenType::LONG_LITERAL: return "LONG_LITERAL";
        case TokenType::STRING_LITERAL: return "STRING_LITERAL";
        
        case TokenType::IDENTIFIER: return "IDENTIFIER";
        case TokenType::END_OF_FILE: return "END_OF_FILE";

        case TokenType::TYPEDEF: return "TYPEDEF";

        case TokenType::UNKNOWN: return "UNKNOWN";
        
        default: return "UNDEFINED";
    }
}
