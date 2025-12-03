#include "scanner.h"
#include <cctype>

Scanner::Scanner(string source) : source(source), start(0), current(0), line(1), column(1) {
    initKeywords();
}

void Scanner::initKeywords() {
    keywords["int"] = TokenType::INT;
    keywords["float"] = TokenType::FLOAT;
    keywords["long"] = TokenType::LONG;
    keywords["unsigned"] = TokenType::UNSIGNED;
    keywords["if"] = TokenType::IF;
    keywords["else"] = TokenType::ELSE;
    keywords["while"] = TokenType::WHILE;
    keywords["for"] = TokenType::FOR;
    keywords["return"] = TokenType::RETURN;
    keywords["printf"] = TokenType::PRINTF;
    keywords["include"] = TokenType::INCLUDE;
}

vector<Token> Scanner::scanTokens() {
    while (!isAtEnd()) {
        start = current;
        scanToken();
    }
    tokens.push_back(Token(TokenType::END_OF_FILE, "", line, column));
    return tokens;
}

bool Scanner::isAtEnd() {
    return current >= source.length();
}

char Scanner::advance() {
    column++;
    return source[current++];
}

char Scanner::peek() {
    if (isAtEnd()) return '\0';
    return source[current];
}

char Scanner::peekNext() {
    if (current + 1 >= source.length()) return '\0';
    return source[current + 1];
}

bool Scanner::match(char expected) {
    if (isAtEnd()) return false;
    if (source[current] != expected) return false;
    current++;
    column++;
    return true;
}

void Scanner::addToken(TokenType type) {
    string text = source.substr(start, current - start);
    tokens.push_back(Token(type, text, line, column - text.length()));
}

void Scanner::addToken(TokenType type, string lexeme) {
    tokens.push_back(Token(type, lexeme, line, column - lexeme.length()));
}

void Scanner::scanToken() {
    char c = advance();
    switch (c) {
        case ' ':
        case '\r':
        case '\t':
            break;
        case '\n':
            line++;
            column = 1;
            break;
        case '(': addToken(TokenType::LPAREN); break;
        case ')': addToken(TokenType::RPAREN); break;
        case '{': addToken(TokenType::LBRACE); break;
        case '}': addToken(TokenType::RBRACE); break;
        case '[': addToken(TokenType::LBRACKET); break;
        case ']': addToken(TokenType::RBRACKET); break;
        case ';': addToken(TokenType::SEMICOLON); break;
        case ',': addToken(TokenType::COMMA); break;
        case '%': addToken(TokenType::MODULO); break;
        case '+':
            if (match('+')) {
                addToken(TokenType::INCREMENT);
            } else if (match('=')) {
                addToken(TokenType::PLUSEQ);
            } else {
                addToken(TokenType::PLUS);
            }
            break;
        case '-':
            if (match('-')) {
                addToken(TokenType::DECREMENT);
            } else if (match('=')) {
                addToken(TokenType::MINUSEQ);
            } else {
                addToken(TokenType::MINUS);
            }
            break;
        case '*':
            addToken(TokenType::MULTIPLY);
            break;
        case '/':
            if (match('/')) {
                while (peek() != '\n' && !isAtEnd()) advance();
            } else if (match('*')) {
                while (!isAtEnd()) {
                    if (peek() == '*' && peekNext() == '/') {
                        advance();
                        advance();
                        break;
                    }
                    if (peek() == '\n') {
                        line++;
                        column = 0;
                    }
                    advance();
                }
            } else {
                addToken(TokenType::DIVIDE);
            }
            break;
        case '=':
            addToken(match('=') ? TokenType::EQ : TokenType::ASSIGN);
            break;
        case '!':
            if (match('=')) {
                addToken(TokenType::NE);
            } else {
                addToken(TokenType::NOT);
            }
            break;
        case '<':
            addToken(match('=') ? TokenType::LE : TokenType::LT);
            break;
        case '>':
            addToken(match('=') ? TokenType::GE : TokenType::GT);
            break;
        case '&':
            if (match('&')) {
                addToken(TokenType::AND);
            }
            break;
        case '|':
            if (match('|')) {
                addToken(TokenType::OR);
            }
            break;
        case '"':
            scanString();
            break;
        case '#':
            while (peek() != '\n' && !isAtEnd()) advance();
            break;
        default:
            if (isDigit(c)) {
                number();
            } else if (isAlpha(c)) {
                identifier();
            } else {
                addToken(TokenType::UNKNOWN);
            }
            break;
    }
}

void Scanner::identifier() {
    while (isAlphaNumeric(peek())) advance();
    string text = source.substr(start, current - start);
    TokenType type = TokenType::IDENTIFIER;
    if (keywords.find(text) != keywords.end()) {
        type = keywords[text];
    }
    addToken(type, text);
}

void Scanner::number() {
    bool isFloat = false;
    bool isLong = false;
    while (isDigit(peek())) advance();
    if (peek() == '.' && isDigit(peekNext())) {
        isFloat = true;
        advance();
        while (isDigit(peek())) advance();
    }
    if (peek() == 'L' || peek() == 'l') {
        isLong = true;
        advance();
    }
    string text = source.substr(start, current - start);
    if (isFloat) {
        addToken(TokenType::FLOAT_LITERAL, text);
    } else if (isLong) {
        addToken(TokenType::LONG_LITERAL, text);
    } else {
        addToken(TokenType::INT_LITERAL, text);
    }
}

void Scanner::scanString() {
    while (peek() != '"' && !isAtEnd()) {
        if (peek() == '\n') {
            line++;
            column = 0;
        }
        advance();
    }
    if (isAtEnd()) {
        return;
    }
    advance();
    string value = source.substr(start + 1, current - start - 2);
    addToken(TokenType::STRING_LITERAL, value);
}

bool Scanner::isDigit(char c) {
    return c >= '0' && c <= '9';
}

bool Scanner::isAlpha(char c) {
    return (c >= 'a' && c <= 'z') ||
           (c >= 'A' && c <= 'Z') ||
           c == '_';
}

bool Scanner::isAlphaNumeric(char c) {
    return isAlpha(c) || isDigit(c);
}
