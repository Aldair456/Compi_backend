#include "ast.h"

string dataTypeToString(DataType type) {
    switch(type) {
        case DataType::INT: return "int";
        case DataType::FLOAT: return "float";
        case DataType::LONG: return "long";
        case DataType::UNSIGNED_INT: return "unsigned int";
        case DataType::VOID: return "void";
        default: return "unknown";
    }
}

IntLiteral::IntLiteral(int value) : value(value) {
    inferredType = DataType::INT;
}

void IntLiteral::accept(Visitor* visitor) {
    visitor->visitIntLiteral(this);
}

FloatLiteral::FloatLiteral(float value) : value(value) {
    inferredType = DataType::FLOAT;
}

void FloatLiteral::accept(Visitor* visitor) {
    visitor->visitFloatLiteral(this);
}

LongLiteral::LongLiteral(long value) : value(value) {
    inferredType = DataType::LONG;
}

void LongLiteral::accept(Visitor* visitor) {
    visitor->visitLongLiteral(this);
}

StringLiteral::StringLiteral(string value) : value(value) {
    inferredType = DataType::UNKNOWN;
}

void StringLiteral::accept(Visitor* visitor) {
    visitor->visitStringLiteral(this);
}

Variable::Variable(string name) : name(name) {}

void Variable::accept(Visitor* visitor) {
    visitor->visitVariable(this);
}

BinaryOp::BinaryOp(unique_ptr<Expr> left, Token op, unique_ptr<Expr> right)
    : left(move(left)), op(op), right(move(right)) {}

void BinaryOp::accept(Visitor* visitor) {
    visitor->visitBinaryOp(this);
}

UnaryOp::UnaryOp(Token op, unique_ptr<Expr> operand)
    : op(op), operand(move(operand)) {}

void UnaryOp::accept(Visitor* visitor) {
    visitor->visitUnaryOp(this);
}

CastExpr::CastExpr(DataType targetType, unique_ptr<Expr> expr)
    : targetType(targetType), expr(move(expr)) {
    inferredType = targetType;
}

void CastExpr::accept(Visitor* visitor) {
    visitor->visitCastExpr(this);
}

TernaryExpr::TernaryExpr(unique_ptr<Expr> condition, unique_ptr<Expr> exprTrue, unique_ptr<Expr> exprFalse)
    : condition(move(condition)), exprTrue(move(exprTrue)), exprFalse(move(exprFalse)) {}

void TernaryExpr::accept(Visitor* visitor) {
    visitor->visitTernaryExpr(this);
}

CallExpr::CallExpr(string functionName, vector<unique_ptr<Expr>> arguments)
    : functionName(functionName), arguments(move(arguments)) {}

void CallExpr::accept(Visitor* visitor) {
    visitor->visitCallExpr(this);
}

ArrayAccess::ArrayAccess(string arrayName, vector<unique_ptr<Expr>> indices)
    : arrayName(arrayName), indices(move(indices)) {}

void ArrayAccess::accept(Visitor* visitor) {
    visitor->visitArrayAccess(this);
}

AssignExpr::AssignExpr(string varName, unique_ptr<Expr> value)
    : varName(varName), value(move(value)), isArrayAssign(false) {}

AssignExpr::AssignExpr(string varName, vector<unique_ptr<Expr>> indices, unique_ptr<Expr> value)
    : varName(varName), indices(move(indices)), value(move(value)), isArrayAssign(true) {}

void AssignExpr::accept(Visitor* visitor) {
    visitor->visitAssignExpr(this);
}

VarDecl::VarDecl(DataType type, string name, unique_ptr<Expr> initializer)
    : type(type), name(name), initializer(move(initializer)), isArray(false) {}

VarDecl::VarDecl(DataType type, string name, vector<int> dimensions)
    : type(type), name(name), isArray(true), dimensions(dimensions) {}

void VarDecl::accept(Visitor* visitor) {
    visitor->visitVarDecl(this);
}

AssignStmt::AssignStmt(string varName, unique_ptr<Expr> value)
    : varName(varName), value(move(value)), isArrayAssign(false) {}

AssignStmt::AssignStmt(string varName, vector<unique_ptr<Expr>> indices, unique_ptr<Expr> value)
    : varName(varName), indices(move(indices)), value(move(value)), isArrayAssign(true) {}

void AssignStmt::accept(Visitor* visitor) {
    visitor->visitAssignStmt(this);
}

Block::Block(vector<unique_ptr<Stmt>> statements)
    : statements(move(statements)) {}

void Block::accept(Visitor* visitor) {
    visitor->visitBlock(this);
}

IfStmt::IfStmt(unique_ptr<Expr> condition, unique_ptr<Stmt> thenBranch, unique_ptr<Stmt> elseBranch)
    : condition(move(condition)), thenBranch(move(thenBranch)), elseBranch(move(elseBranch)) {}

void IfStmt::accept(Visitor* visitor) {
    visitor->visitIfStmt(this);
}

WhileStmt::WhileStmt(unique_ptr<Expr> condition, unique_ptr<Stmt> body)
    : condition(move(condition)), body(move(body)) {}

void WhileStmt::accept(Visitor* visitor) {
    visitor->visitWhileStmt(this);
}

ForStmt::ForStmt(unique_ptr<Stmt> initializer, unique_ptr<Expr> condition,
                 unique_ptr<Expr> increment, unique_ptr<Stmt> body)
    : initializer(move(initializer)), condition(move(condition)),
      increment(move(increment)), body(move(body)) {}

void ForStmt::accept(Visitor* visitor) {
    visitor->visitForStmt(this);
}

ReturnStmt::ReturnStmt(unique_ptr<Expr> value)
    : value(move(value)) {}

void ReturnStmt::accept(Visitor* visitor) {
    visitor->visitReturnStmt(this);
}

ExprStmt::ExprStmt(unique_ptr<Expr> expression)
    : expression(move(expression)) {}

void ExprStmt::accept(Visitor* visitor) {
    visitor->visitExprStmt(this);
}

FunctionDecl::FunctionDecl(DataType returnType, string name,
                           vector<pair<DataType, string>> parameters,
                           unique_ptr<Block> body)
    : returnType(returnType), name(name), parameters(parameters), body(move(body)) {}

void FunctionDecl::accept(Visitor* visitor) {
    visitor->visitFunctionDecl(this);
}

Program::Program(vector<unique_ptr<Stmt>> statements)
    : statements(move(statements)) {}
