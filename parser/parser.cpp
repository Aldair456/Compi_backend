#include "parser.h"
#include <iostream>

Parser::Parser(vector<Token> tokens) : tokens(tokens), current(0) {
    // Initialize global scope
    scopes.push_back(map<string, DataType>());
}

Token Parser::peek() {
    return tokens[current];
}

Token Parser::previous() {
    return tokens[current - 1];
}

Token Parser::advance() {
    if (!isAtEnd()) current++;
    return previous();
}

bool Parser::isAtEnd() {
    return peek().type == TokenType::END_OF_FILE;
}

bool Parser::check(TokenType type) {
    if (isAtEnd()) return false;
    return peek().type == type;
}

bool Parser::match(vector<TokenType> types) {
    for (TokenType type : types) {
        if (check(type)) {
            advance();
            return true;
        }
    }
    return false;
}

Token Parser::consume(TokenType type, string message) {
    if (check(type)) return advance();
    error(message);
    throw runtime_error(message);
}

void Parser::error(string message) {
    Token token = peek();
    cerr << "Parse error at line " << token.line << ": " << message << endl;
}

void Parser::synchronize() {
    advance();
    while (!isAtEnd()) {
        if (previous().type == TokenType::SEMICOLON) return;
        switch (peek().type) {
            case TokenType::IF:
            case TokenType::WHILE:
            case TokenType::FOR:
            case TokenType::RETURN:
            case TokenType::INT:
            case TokenType::FLOAT:
            case TokenType::LONG:
            case TokenType::UNSIGNED:
                return;
            default: break;
        }
        advance();
    }
}

// Symbol Table Management
void Parser::enterScope() {
    scopes.push_back(map<string, DataType>());
}

void Parser::exitScope() {
    if (scopes.size() > 1) {
        scopes.pop_back();
    }
}

void Parser::declareVariable(string name, DataType type) {
    if (scopes.empty()) return;
    scopes.back()[name] = type;
}

DataType Parser::getVariableType(string name) {
    for (int i = scopes.size() - 1; i >= 0; i--) {
        if (scopes[i].find(name) != scopes[i].end()) {
            return scopes[i][name];
        }
    }
    return DataType::UNKNOWN;
}

DataType Parser::tokenToDataType(Token token) {
    switch(token.type) {
        case TokenType::INT: return DataType::INT;
        case TokenType::FLOAT: return DataType::FLOAT;
        case TokenType::LONG: return DataType::LONG;
        case TokenType::UNSIGNED: return DataType::UNSIGNED_INT;
        case TokenType::IDENTIFIER:
            if (typeAliases.count(token.lexeme)) {
                return typeAliases[token.lexeme];
            }
            return DataType::UNKNOWN;
        default: return DataType::UNKNOWN;
    }
}

unique_ptr<Program> Parser::parse() {
    vector<unique_ptr<Stmt>> statements;
    while (!isAtEnd()) {
        try {
            statements.push_back(declaration());
        } catch (runtime_error& e) {
            synchronize();
        }
    }
    return make_unique<Program>(move(statements));
}

unique_ptr<Stmt> Parser::declaration() {
    if (match({TokenType::TYPEDEF})) {
        Token typeToken = advance();
        DataType baseType = tokenToDataType(typeToken);
        Token aliasName = consume(TokenType::IDENTIFIER, "Expect alias name.");
        consume(TokenType::SEMICOLON, "Expect ';' after typedef.");
        typeAliases[aliasName.lexeme] = baseType;
        return make_unique<Block>(vector<unique_ptr<Stmt>>());
    }

    if (check(TokenType::INT) || check(TokenType::FLOAT) ||
        check(TokenType::LONG) || check(TokenType::UNSIGNED) ||
        isTypeAlias(peek())) {

        Token typeToken = advance();
        DataType type = tokenToDataType(typeToken);
        Token name = consume(TokenType::IDENTIFIER, "Expected variable or function name.");

        if (check(TokenType::LPAREN)) {
            advance();
            vector<pair<DataType, string>> parameters;
            if (!check(TokenType::RPAREN)) {
                do {
                    Token paramTypeToken = advance();
                    DataType paramType = tokenToDataType(paramTypeToken);
                    Token paramName = consume(TokenType::IDENTIFIER, "Expected parameter name.");
                    parameters.push_back({paramType, paramName.lexeme});
                } while (match({TokenType::COMMA}));
            }
            consume(TokenType::RPAREN, "Expected ')' after parameters.");
            consume(TokenType::LBRACE, "Expected '{' before function body.");
            enterScope();
            for (auto& param : parameters) declareVariable(param.second, param.first);
            unique_ptr<Block> body = block();
            exitScope();
            unique_ptr<FunctionDecl> func = make_unique<FunctionDecl>(type, name.lexeme, parameters, move(body));
            func->line = name.line;
            return func;
        }

        if (match({TokenType::LBRACKET})) {
            vector<int> dimensions;
            do {
                Token sizeToken = consume(TokenType::INT_LITERAL, "Expected array size.");
                dimensions.push_back(stoi(sizeToken.lexeme));
                consume(TokenType::RBRACKET, "Expected ']'.");
            } while (match({TokenType::LBRACKET}));
            unique_ptr<VarDecl> varDecl = make_unique<VarDecl>(type, name.lexeme, dimensions);
            varDecl->line = name.line;
            if (match({TokenType::ASSIGN})) {
                consume(TokenType::LBRACE, "Expect '{'");
                int c = 1; while(c>0 && !isAtEnd()) { if(check(TokenType::LBRACE)) c++; if(check(TokenType::RBRACE)) c--; advance(); }
            }
            consume(TokenType::SEMICOLON, "Expected ';'");
            declareVariable(name.lexeme, type);
            return varDecl;
        }

        unique_ptr<Expr> initializer = nullptr;
        if (match({TokenType::ASSIGN})) {
            initializer = expression();
        }
        consume(TokenType::SEMICOLON, "Expected ';' after variable declaration.");
        unique_ptr<VarDecl> varDecl = make_unique<VarDecl>(type, name.lexeme, move(initializer));
        varDecl->line = name.line;
        declareVariable(name.lexeme, type);
        return varDecl;
    }
    return statement();
}

unique_ptr<Stmt> Parser::statement() {
    if (match({TokenType::IF})) return ifStatement();
    if (match({TokenType::WHILE})) return whileStatement();
    if (match({TokenType::FOR})) return forStatement();
    if (match({TokenType::RETURN})) return returnStatement();
    if (match({TokenType::LBRACE})) return block();
    return exprStatement();
}

unique_ptr<Stmt> Parser::exprStatement() {
    if (check(TokenType::IDENTIFIER)) {
        Token name = peek();
        int savedPos = current;
        advance();
        if (match({TokenType::ASSIGN, TokenType::PLUSEQ, TokenType::MINUSEQ})) {
            Token op = previous();
            unique_ptr<Expr> value = expression();
            if (op.type == TokenType::PLUSEQ) {
                value = make_unique<BinaryOp>(make_unique<Variable>(name.lexeme), Token(TokenType::PLUS, "+", op.line, op.column), move(value));
            } else if (op.type == TokenType::MINUSEQ) {
                value = make_unique<BinaryOp>(make_unique<Variable>(name.lexeme), Token(TokenType::MINUS, "-", op.line, op.column), move(value));
            }
            consume(TokenType::SEMICOLON, "Expected ';' after assignment.");
            unique_ptr<AssignStmt> assign = make_unique<AssignStmt>(name.lexeme, move(value));
            assign->line = name.line;
            return assign;
        }
        if (check(TokenType::LBRACKET)) {
            vector<unique_ptr<Expr>> indices;
            while (match({TokenType::LBRACKET})) {
                indices.push_back(expression());
                consume(TokenType::RBRACKET, "Expected ']'.");
            }
            if (match({TokenType::ASSIGN})) {
                unique_ptr<Expr> value = expression();
                consume(TokenType::SEMICOLON, "Expected ';' after assignment.");
                unique_ptr<AssignStmt> assign = make_unique<AssignStmt>(name.lexeme, move(indices), move(value));
                assign->line = name.line;
                return assign;
            }
        }
        current = savedPos;
    }
    Token startToken = peek();
    unique_ptr<Expr> expr = expression();
    consume(TokenType::SEMICOLON, "Expected ';' after expression.");
    unique_ptr<ExprStmt> exprStmt = make_unique<ExprStmt>(move(expr));
    exprStmt->line = startToken.line;
    return exprStmt;
}

unique_ptr<Stmt> Parser::ifStatement() {
    Token ifToken = previous();
    consume(TokenType::LPAREN, "Expected '(' after 'if'.");
    unique_ptr<Expr> condition = expression();
    consume(TokenType::RPAREN, "Expected ')' after if condition.");
    unique_ptr<Stmt> thenBranch = statement();
    unique_ptr<Stmt> elseBranch = nullptr;
    if (match({TokenType::ELSE})) elseBranch = statement();
    unique_ptr<IfStmt> ifStmt = make_unique<IfStmt>(move(condition), move(thenBranch), move(elseBranch));
    ifStmt->line = ifToken.line;
    return ifStmt;
}

unique_ptr<Stmt> Parser::whileStatement() {
    Token whileToken = previous();
    consume(TokenType::LPAREN, "Expected '(' after 'while'.");
    unique_ptr<Expr> condition = expression();
    consume(TokenType::RPAREN, "Expected ')' after while condition.");
    unique_ptr<Stmt> body = statement();
    unique_ptr<WhileStmt> whileStmt = make_unique<WhileStmt>(move(condition), move(body));
    whileStmt->line = whileToken.line;
    return whileStmt;
}

unique_ptr<Stmt> Parser::forStatement() {
    Token forToken = previous();
    consume(TokenType::LPAREN, "Expected '(' after 'for'.");
    unique_ptr<Stmt> initializer = nullptr;
    if (match({TokenType::INT, TokenType::FLOAT, TokenType::LONG, TokenType::UNSIGNED})) {
        Token typeToken = previous();
        DataType type = tokenToDataType(typeToken);
        Token name = consume(TokenType::IDENTIFIER, "Expected variable name.");
        unique_ptr<Expr> init = nullptr;
        if (match({TokenType::ASSIGN})) init = expression();
        consume(TokenType::SEMICOLON, "Expected ';' after for initializer.");
        initializer = make_unique<VarDecl>(type, name.lexeme, move(init));
        initializer->line = name.line;
    } else if (!check(TokenType::SEMICOLON)) {
        initializer = exprStatement();
    } else {
        advance();
    }
    unique_ptr<Expr> condition = nullptr;
    if (!check(TokenType::SEMICOLON)) condition = expression();
    consume(TokenType::SEMICOLON, "Expected ';' after for condition.");
    unique_ptr<Expr> increment = nullptr;
    if (!check(TokenType::RPAREN)) increment = expression();
    consume(TokenType::RPAREN, "Expected ')' after for clauses.");
    unique_ptr<Stmt> body = statement();
    unique_ptr<ForStmt> forStmt = make_unique<ForStmt>(move(initializer), move(condition), move(increment), move(body));
    forStmt->line = forToken.line;
    return forStmt;
}

unique_ptr<Stmt> Parser::returnStatement() {
    Token returnToken = previous();
    unique_ptr<Expr> value = nullptr;
    if (!check(TokenType::SEMICOLON)) value = expression();
    consume(TokenType::SEMICOLON, "Expected ';' after return value.");
    unique_ptr<ReturnStmt> retStmt = make_unique<ReturnStmt>(move(value));
    retStmt->line = returnToken.line;
    return retStmt;
}

unique_ptr<Block> Parser::block() {
    enterScope();
    vector<unique_ptr<Stmt>> statements;
    while (!check(TokenType::RBRACE) && !isAtEnd()) statements.push_back(declaration());
    consume(TokenType::RBRACE, "Expected '}' after block.");
    exitScope();
    return make_unique<Block>(move(statements));
}

unique_ptr<Expr> Parser::expression() {
    return assignment();
}

unique_ptr<Expr> Parser::assignment() {
    unique_ptr<Expr> expr = ternary();
    if (match({TokenType::ASSIGN, TokenType::PLUSEQ, TokenType::MINUSEQ})) {
        Token op = previous();
        unique_ptr<Expr> value = assignment();
        Variable* var = dynamic_cast<Variable*>(expr.get());
        if (!var) {
            error("Left side of assignment must be a variable.");
            throw runtime_error("Left side of assignment must be a variable.");
        }
        if (op.type == TokenType::PLUSEQ) {
            value = make_unique<BinaryOp>(make_unique<Variable>(var->name), Token(TokenType::PLUS, "+", op.line, op.column), move(value));
        } else if (op.type == TokenType::MINUSEQ) {
            value = make_unique<BinaryOp>(make_unique<Variable>(var->name), Token(TokenType::MINUS, "-", op.line, op.column), move(value));
        }
        DataType varType = getVariableType(var->name);
        DataType valType = value->inferredType;
        if (varType == DataType::FLOAT && valType == DataType::INT) value = make_unique<CastExpr>(DataType::FLOAT, move(value));
        else if (varType == DataType::INT && valType == DataType::FLOAT) value = make_unique<CastExpr>(DataType::INT, move(value));
        unique_ptr<AssignExpr> assignExpr = make_unique<AssignExpr>(var->name, move(value));
        assignExpr->line = op.line;
        return assignExpr;
    }
    if (ArrayAccess* arrAccess = dynamic_cast<ArrayAccess*>(expr.get())) {
        if (match({TokenType::ASSIGN})) {
            Token assignToken = previous();
            unique_ptr<Expr> value = assignment();
            DataType arrType = getVariableType(arrAccess->arrayName);
            DataType valType = value->inferredType;
            if (arrType == DataType::FLOAT && valType == DataType::INT) value = make_unique<CastExpr>(DataType::FLOAT, move(value));
            else if (arrType == DataType::INT && valType == DataType::FLOAT) value = make_unique<CastExpr>(DataType::INT, move(value));
            unique_ptr<AssignExpr> assignExpr = make_unique<AssignExpr>(arrAccess->arrayName, move(arrAccess->indices), move(value));
            assignExpr->line = assignToken.line;
            return assignExpr;
        }
    }
    return expr;
}

unique_ptr<Expr> Parser::ternary() {
    unique_ptr<Expr> expr = logicalOr();
    return expr;
}

unique_ptr<Expr> Parser::logicalOr() {
    unique_ptr<Expr> expr = logicalAnd();
    while (match({TokenType::OR})) {
        Token op = previous();
        unique_ptr<Expr> right = logicalAnd();
        expr = make_unique<BinaryOp>(move(expr), op, move(right));
    }
    return expr;
}

unique_ptr<Expr> Parser::logicalAnd() {
    unique_ptr<Expr> expr = equality();
    while (match({TokenType::AND})) {
        Token op = previous();
        unique_ptr<Expr> right = equality();
        expr = make_unique<BinaryOp>(move(expr), op, move(right));
    }
    return expr;
}

unique_ptr<Expr> Parser::equality() {
    unique_ptr<Expr> expr = comparison();
    while (match({TokenType::EQ, TokenType::NE})) {
        Token op = previous();
        unique_ptr<Expr> right = comparison();
        DataType leftType = expr->inferredType;
        DataType rightType = right->inferredType;
        if (leftType == DataType::INT && rightType == DataType::FLOAT) expr = make_unique<CastExpr>(DataType::FLOAT, move(expr));
        else if (leftType == DataType::FLOAT && rightType == DataType::INT) right = make_unique<CastExpr>(DataType::FLOAT, move(right));
        auto binaryOp = make_unique<BinaryOp>(move(expr), op, move(right));
        binaryOp->inferredType = DataType::INT;
        binaryOp->line = op.line;
        expr = move(binaryOp);
    }
    return expr;
}

unique_ptr<Expr> Parser::comparison() {
    unique_ptr<Expr> expr = term();
    while (match({TokenType::LT, TokenType::GT, TokenType::LE, TokenType::GE})) {
        Token op = previous();
        unique_ptr<Expr> right = term();
        DataType leftType = expr->inferredType;
        DataType rightType = right->inferredType;
        if (leftType == DataType::INT && rightType == DataType::FLOAT) expr = make_unique<CastExpr>(DataType::FLOAT, move(expr));
        else if (leftType == DataType::FLOAT && rightType == DataType::INT) right = make_unique<CastExpr>(DataType::FLOAT, move(right));
        auto binaryOp = make_unique<BinaryOp>(move(expr), op, move(right));
        binaryOp->inferredType = DataType::INT;
        binaryOp->line = op.line;
        expr = move(binaryOp);
    }
    return expr;
}

unique_ptr<Expr> Parser::term() {
    unique_ptr<Expr> expr = factor();
    while (match({TokenType::PLUS, TokenType::MINUS})) {
        Token op = previous();
        unique_ptr<Expr> right = factor();
        DataType leftType = expr->inferredType;
        DataType rightType = right->inferredType;
        DataType targetType = getDominantType(leftType, rightType);
        if (leftType != targetType) expr = make_unique<CastExpr>(targetType, move(expr));
        if (rightType != targetType) right = make_unique<CastExpr>(targetType, move(right));
        auto binaryOp = make_unique<BinaryOp>(move(expr), op, move(right));
        binaryOp->inferredType = targetType;
        binaryOp->line = op.line;
        expr = move(binaryOp);
    }
    return expr;
}

unique_ptr<Expr> Parser::factor() {
    unique_ptr<Expr> expr = unary();
    while (match({TokenType::MULTIPLY, TokenType::DIVIDE, TokenType::MODULO})) {
        Token op = previous();
        unique_ptr<Expr> right = unary();
        DataType leftType = expr->inferredType;
        DataType rightType = right->inferredType;
        DataType resultType = leftType;
        if (leftType == DataType::INT && rightType == DataType::FLOAT) { expr = make_unique<CastExpr>(DataType::FLOAT, move(expr)); resultType = DataType::FLOAT; }
        else if (leftType == DataType::FLOAT && rightType == DataType::INT) { right = make_unique<CastExpr>(DataType::FLOAT, move(right)); resultType = DataType::FLOAT; }
        else if (leftType == DataType::FLOAT || rightType == DataType::FLOAT) resultType = DataType::FLOAT;
        auto binaryOp = make_unique<BinaryOp>(move(expr), op, move(right));
        binaryOp->inferredType = resultType;
        binaryOp->line = op.line;
        expr = move(binaryOp);
    }
    return expr;
}

unique_ptr<Expr> Parser::unary() {
    if (match({TokenType::MINUS, TokenType::NOT})) {
        Token op = previous();
        unique_ptr<Expr> right = unary();
        return make_unique<UnaryOp>(op, move(right));
    }
    return cast();
}

unique_ptr<Expr> Parser::cast() {
    if (check(TokenType::LPAREN)) {
        int savedPos = current;
        advance();
        if (match({TokenType::INT, TokenType::FLOAT, TokenType::LONG, TokenType::UNSIGNED})) {
            Token typeToken = previous();
            DataType targetType = tokenToDataType(typeToken);
            if (match({TokenType::RPAREN})) {
                unique_ptr<Expr> expr = cast();
                unique_ptr<CastExpr> castExpr = make_unique<CastExpr>(targetType, move(expr));
                castExpr->line = typeToken.line;
                return castExpr;
            }
        }
        current = savedPos;
    }
    return postfix();
}

unique_ptr<Expr> Parser::postfix() {
    unique_ptr<Expr> expr = primary();
    if (Variable* var = dynamic_cast<Variable*>(expr.get())) {
        if (check(TokenType::LBRACKET)) {
            string arrayName = var->name;
            vector<unique_ptr<Expr>> indices;
            Token bracketToken = peek();
            while (match({TokenType::LBRACKET})) {
                indices.push_back(expression());
                consume(TokenType::RBRACKET, "Expected ']'.");
            }
            unique_ptr<ArrayAccess> arrAccess = make_unique<ArrayAccess>(arrayName, move(indices));
            arrAccess->line = bracketToken.line;
            expr = move(arrAccess);
        }
    }
    while (match({TokenType::INCREMENT, TokenType::DECREMENT})) {
        Token op = previous();
        if (Variable* var = dynamic_cast<Variable*>(expr.get())) {
            TokenType binOp = (op.type == TokenType::INCREMENT) ? TokenType::PLUS : TokenType::MINUS;
            unique_ptr<Expr> one = make_unique<IntLiteral>(1);
            one->line = op.line;
            unique_ptr<BinaryOp> addExpr = make_unique<BinaryOp>(
                make_unique<Variable>(var->name),
                Token(binOp, op.type == TokenType::INCREMENT ? "+" : "-", op.line, op.column),
                move(one)
            );
            addExpr->line = op.line;
            unique_ptr<AssignExpr> assignExpr = make_unique<AssignExpr>(var->name, move(addExpr));
            assignExpr->line = op.line;
            expr = move(assignExpr);
        } else {
            expr = make_unique<UnaryOp>(op, move(expr));
        }
    }
    return expr;
}

unique_ptr<Expr> Parser::primary() {
    // 1. Enteros y Largos (con try-catch para desbordamiento)
    if (match({TokenType::INT_LITERAL})) {
        Token token = previous();
        try {
            int val = stoi(token.lexeme);
            unique_ptr<IntLiteral> lit = make_unique<IntLiteral>(val);
            lit->line = token.line;
            return lit;
        } catch (const std::out_of_range& e) {
            // Desbordamiento de int -> Promocionar a Long
            long long val = stoll(token.lexeme);
            unique_ptr<LongLiteral> lit = make_unique<LongLiteral>(val);
            lit->line = token.line;
            return lit;
        }
    }

    // 2. Flotantes
    if (match({TokenType::FLOAT_LITERAL})) {
        Token token = previous();
        unique_ptr<FloatLiteral> lit = make_unique<FloatLiteral>(stof(token.lexeme));
        lit->line = token.line;
        return lit;
    }

    // 3. Literales Long Explícitos (123L)
    if (match({TokenType::LONG_LITERAL})) {
        Token token = previous();
        string lexeme = token.lexeme;
        if (lexeme.back() == 'L' || lexeme.back() == 'l') lexeme.pop_back();
        unique_ptr<LongLiteral> lit = make_unique<LongLiteral>(stoll(lexeme));
        lit->line = token.line;
        return lit;
    }

    // 4. Strings
    if (match({TokenType::STRING_LITERAL})) {
        Token token = previous();
        unique_ptr<StringLiteral> lit = make_unique<StringLiteral>(token.lexeme);
        lit->line = token.line;
        return lit;
    }

    // 5. Identificadores y Printf
    if (match({TokenType::IDENTIFIER, TokenType::PRINTF})) {
        Token name = previous();
        if (name.type == TokenType::PRINTF) name.lexeme = "printf";

        if (match({TokenType::LPAREN})) {
            vector<unique_ptr<Expr>> arguments;
            if (!check(TokenType::RPAREN)) {
                do {
                    arguments.push_back(expression());
                } while (match({TokenType::COMMA}));
            }
            consume(TokenType::RPAREN, "Expected ')' after arguments.");
            unique_ptr<CallExpr> call = make_unique<CallExpr>(name.lexeme, move(arguments));
            call->line = name.line;
            return call;
        }

        unique_ptr<Variable> var = make_unique<Variable>(name.lexeme);
        var->line = name.line;
        var->inferredType = getVariableType(name.lexeme);
        return var;
    }

    // 6. Expresiones Agrupadas (Paréntesis)
    if (match({TokenType::LPAREN})) {
        unique_ptr<Expr> expr = expression();
        consume(TokenType::RPAREN, "Expected ')' after expression.");
        return expr;
    }

    error("Expected expression.");
    throw runtime_error("Expected expression.");
}

DataType Parser::getDominantType(DataType t1, DataType t2) {
    if (t1 == DataType::FLOAT || t2 == DataType::FLOAT) return DataType::FLOAT;
    if (t1 == DataType::LONG || t2 == DataType::LONG) return DataType::LONG;
    if (t1 == DataType::UNSIGNED_INT || t2 == DataType::UNSIGNED_INT) return DataType::UNSIGNED_INT;
    return DataType::INT;
}

bool Parser::isTypeAlias(Token token) {
    return token.type == TokenType::IDENTIFIER &&
           typeAliases.find(token.lexeme) != typeAliases.end();
}