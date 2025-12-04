#ifndef AST_H
#define AST_H

#include <string>
#include <vector>
#include <memory>
#include "../scanner/token.h"

using namespace std;

class Visitor;

enum class DataType {
    INT,
    FLOAT,
    LONG,
    UNSIGNED_INT,
    VOID,
    UNKNOWN
};

string dataTypeToString(DataType type);

class Expr {
public:
    virtual ~Expr() = default;
    virtual void accept(Visitor* visitor) = 0;
    DataType inferredType = DataType::UNKNOWN;
    int line = 1;
};

class Stmt {
public:
    virtual ~Stmt() = default;
    virtual void accept(Visitor* visitor) = 0;
    int line = 1;
};

class IntLiteral : public Expr {
public:
    int value;
    IntLiteral(int value);
    void accept(Visitor* visitor) override;
};

class FloatLiteral : public Expr {
public:
    float value;
    FloatLiteral(float value);
    void accept(Visitor* visitor) override;
};

class LongLiteral : public Expr {
public:
    long long value;
    LongLiteral(long long value);
    void accept(Visitor* visitor) override;
};

class StringLiteral : public Expr {
public:
    string value;
    StringLiteral(string value);
    void accept(Visitor* visitor) override;
};

class Variable : public Expr {
public:
    string name;
    Variable(string name);
    void accept(Visitor* visitor) override;
};

class BinaryOp : public Expr {
public:
    unique_ptr<Expr> left;
    Token op;
    unique_ptr<Expr> right;
    
    BinaryOp(unique_ptr<Expr> left, Token op, unique_ptr<Expr> right);
    void accept(Visitor* visitor) override;
};

class UnaryOp : public Expr {
public:
    Token op;
    unique_ptr<Expr> operand;
    
    UnaryOp(Token op, unique_ptr<Expr> operand);
    void accept(Visitor* visitor) override;
};

class CastExpr : public Expr {
public:
    DataType targetType;
    unique_ptr<Expr> expr;
    
    CastExpr(DataType targetType, unique_ptr<Expr> expr);
    void accept(Visitor* visitor) override;
};

class TernaryExpr : public Expr {
public:
    unique_ptr<Expr> condition;
    unique_ptr<Expr> exprTrue;
    unique_ptr<Expr> exprFalse;
    
    TernaryExpr(unique_ptr<Expr> condition, unique_ptr<Expr> exprTrue, unique_ptr<Expr> exprFalse);
    void accept(Visitor* visitor) override;
};

class CallExpr : public Expr {
public:
    string functionName;
    vector<unique_ptr<Expr>> arguments;
    
    CallExpr(string functionName, vector<unique_ptr<Expr>> arguments);
    void accept(Visitor* visitor) override;
};

class ArrayAccess : public Expr {
public:
    string arrayName;
    vector<unique_ptr<Expr>> indices;
    
    ArrayAccess(string arrayName, vector<unique_ptr<Expr>> indices);
    void accept(Visitor* visitor) override;
};

class AssignExpr : public Expr {
public:
    string varName;
    unique_ptr<Expr> value;
    bool isArrayAssign;
    vector<unique_ptr<Expr>> indices;
    
    AssignExpr(string varName, unique_ptr<Expr> value);
    AssignExpr(string varName, vector<unique_ptr<Expr>> indices, unique_ptr<Expr> value);
    void accept(Visitor* visitor) override;
};

class VarDecl : public Stmt {
public:
    DataType type;
    string name;
    unique_ptr<Expr> initializer;
    
    bool isArray;
    vector<int> dimensions;
    vector<unique_ptr<Expr>> arrayInitializer;
    
    VarDecl(DataType type, string name, unique_ptr<Expr> initializer = nullptr);
    VarDecl(DataType type, string name, vector<int> dimensions);
    void accept(Visitor* visitor) override;
};

class AssignStmt : public Stmt {
public:
    string varName;
    unique_ptr<Expr> value;
    
    bool isArrayAssign;
    vector<unique_ptr<Expr>> indices;
    
    AssignStmt(string varName, unique_ptr<Expr> value);
    AssignStmt(string varName, vector<unique_ptr<Expr>> indices, unique_ptr<Expr> value);
    void accept(Visitor* visitor) override;
};

class Block : public Stmt {
public:
    vector<unique_ptr<Stmt>> statements;
    
    Block(vector<unique_ptr<Stmt>> statements);
    void accept(Visitor* visitor) override;
};

class IfStmt : public Stmt {
public:
    unique_ptr<Expr> condition;
    unique_ptr<Stmt> thenBranch;
    unique_ptr<Stmt> elseBranch;
    
    IfStmt(unique_ptr<Expr> condition, unique_ptr<Stmt> thenBranch, unique_ptr<Stmt> elseBranch = nullptr);
    void accept(Visitor* visitor) override;
};

class WhileStmt : public Stmt {
public:
    unique_ptr<Expr> condition;
    unique_ptr<Stmt> body;
    
    WhileStmt(unique_ptr<Expr> condition, unique_ptr<Stmt> body);
    void accept(Visitor* visitor) override;
};

class ForStmt : public Stmt {
public:
    unique_ptr<Stmt> initializer;
    unique_ptr<Expr> condition;
    unique_ptr<Expr> increment;
    unique_ptr<Stmt> body;
    
    ForStmt(unique_ptr<Stmt> initializer, unique_ptr<Expr> condition, 
            unique_ptr<Expr> increment, unique_ptr<Stmt> body);
    void accept(Visitor* visitor) override;
};

class ReturnStmt : public Stmt {
public:
    unique_ptr<Expr> value;
    
    ReturnStmt(unique_ptr<Expr> value = nullptr);
    void accept(Visitor* visitor) override;
};

class ExprStmt : public Stmt {
public:
    unique_ptr<Expr> expression;
    
    ExprStmt(unique_ptr<Expr> expression);
    void accept(Visitor* visitor) override;
};

class FunctionDecl : public Stmt {
public:
    DataType returnType;
    string name;
    vector<pair<DataType, string>> parameters;
    unique_ptr<Block> body;
    
    FunctionDecl(DataType returnType, string name, 
                 vector<pair<DataType, string>> parameters, 
                 unique_ptr<Block> body);
    void accept(Visitor* visitor) override;
};

class Program {
public:
    vector<unique_ptr<Stmt>> statements;
    
    Program(vector<unique_ptr<Stmt>> statements);
    void accept(Visitor* visitor);
    virtual ~Program() = default;
};

class Visitor {
public:
    virtual ~Visitor() = default;
    
    virtual void visitIntLiteral(IntLiteral* node) = 0;
    virtual void visitFloatLiteral(FloatLiteral* node) = 0;
    virtual void visitLongLiteral(LongLiteral* node) = 0;
    virtual void visitStringLiteral(StringLiteral* node) = 0;
    virtual void visitVariable(Variable* node) = 0;
    virtual void visitBinaryOp(BinaryOp* node) = 0;
    virtual void visitUnaryOp(UnaryOp* node) = 0;
    virtual void visitCastExpr(CastExpr* node) = 0;
    virtual void visitTernaryExpr(TernaryExpr* node) = 0;
    virtual void visitCallExpr(CallExpr* node) = 0;
    virtual void visitArrayAccess(ArrayAccess* node) = 0;
    virtual void visitAssignExpr(AssignExpr* node) = 0;
    
    virtual void visitVarDecl(VarDecl* node) = 0;
    virtual void visitAssignStmt(AssignStmt* node) = 0;
    virtual void visitBlock(Block* node) = 0;
    virtual void visitIfStmt(IfStmt* node) = 0;
    virtual void visitWhileStmt(WhileStmt* node) = 0;
    virtual void visitForStmt(ForStmt* node) = 0;
    virtual void visitReturnStmt(ReturnStmt* node) = 0;
    virtual void visitExprStmt(ExprStmt* node) = 0;
    virtual void visitFunctionDecl(FunctionDecl* node) = 0;
};

#endif
