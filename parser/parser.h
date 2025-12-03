#ifndef PARSER_H
#define PARSER_H

#include "ast.h"
#include "../scanner/scanner.h"
#include "../scanner/token.h"
#include <vector>
#include <memory>
#include <stdexcept>

using namespace std;

class Parser {
private:
    vector<Token> tokens;
    int current;
    Token peek();
    Token previous();
    Token advance();
    bool isAtEnd();
    bool check(TokenType type);
    bool match(vector<TokenType> types);
    Token consume(TokenType type, string message);
    DataType tokenToDataType(Token token);
    unique_ptr<Stmt> declaration();
    unique_ptr<Stmt> varDeclaration();
    unique_ptr<Stmt> functionDeclaration();
    unique_ptr<Stmt> statement();
    unique_ptr<Stmt> exprStatement();
    unique_ptr<Stmt> ifStatement();
    unique_ptr<Stmt> whileStatement();
    unique_ptr<Stmt> forStatement();
    unique_ptr<Stmt> returnStatement();
    unique_ptr<Block> block();
    unique_ptr<Expr> expression();
    unique_ptr<Expr> assignment();
    unique_ptr<Expr> ternary();
    unique_ptr<Expr> logicalOr();
    unique_ptr<Expr> logicalAnd();
    unique_ptr<Expr> equality();
    unique_ptr<Expr> comparison();
    unique_ptr<Expr> term();
    unique_ptr<Expr> factor();
    unique_ptr<Expr> unary();
    unique_ptr<Expr> cast();
    unique_ptr<Expr> postfix();
    unique_ptr<Expr> primary();
    void error(string message);
    void synchronize();

public:
    Parser(vector<Token> tokens);
    unique_ptr<Program> parse();
};

#endif
