#ifndef PROYECTO_OPTIMIZER_H
#define PROYECTO_OPTIMIZER_H

#include "../parser/ast.h"
#include <map>
#include <memory>
#include <set>






using namespace std;

class Optimizer {
public:
    Optimizer();

    map<string, int> constantValues;
    void optimize(Program* program);

private:
    unique_ptr<Stmt> tryUnrollLoop(ForStmt* forStmt);

    unique_ptr<Stmt> cloneStmt(Stmt* stmt);

    unique_ptr<Expr> cloneExpr(Expr* expr);
    bool tryUnrollLoop(ForStmt* forStmt, vector<unique_ptr<Stmt>>& output);
    bool tryEvaluateConstantLoop(ForStmt* forStmt, vector<unique_ptr<Stmt>>& output);
    unique_ptr<Expr> optimizeBinaryOp(BinaryOp* node);

    unique_ptr<Expr> optimizeExpr(Expr* expr);

    void optimizeStmt(Stmt* stmt);

    void optimizeBlock(Block* block);

    void eliminateDeadStores(Block* block);
    void getReadVariables(Expr* expr, set<string>& variables);
    void getReadVariablesInStmt(Stmt* stmt, set<string>& variables);

    bool isIntLiteral(Expr* expr, int& value);

    int calculate(int left, TokenType op, int right);
};
#endif
