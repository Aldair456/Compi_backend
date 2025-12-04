#ifndef CODEGEN_H
#define CODEGEN_H

#include "../parser/ast.h"
#include "debuggen.h"
#include <string>
#include <map>
#include <vector>
#include <sstream>
#include <stack>
#include <set>

using namespace std;


struct VarInfo {
    DataType type;
    int offset;
    bool isArray;
    vector<int> dimensions;
};


struct FunctionInfo {
    DataType returnType;
    vector<DataType> paramTypes;
    int stackSize;
};

class CodeGen : public Visitor {
private:
    stringstream output;
    map<string, VarInfo> localVars;
    map<string, VarInfo> globalVars;
    map<string, FunctionInfo> functions;
    set<string> optimizedVars;
    string currentFunction;
    int stackOffset;
    int labelCounter;
    stack<string> regStack;
    bool lastExprWasFloat;
    DebugGen* debugGen;
    int currentSourceLine;
    string sourceCode;
    vector<string> sourceLines;
    string newLabel(string prefix = "L");
    void generar(string code, const string& varName = "", const string& description = "");
    void generarLabel(string label);
    string allocReg(DataType type);
    void freeReg(string reg);
    void generarConversionTipo(DataType from, DataType to, string reg);
    void generarPrologoFuncion(string funcName, int stackSize);
    void generarEpilogoFuncion();
    void generarAccesoArray(string arrayName, vector<unique_ptr<Expr>>& indices);
    int calculateArrayOffset(vector<int>& dimensions, int dimIndex);
    int calculateStackSize(FunctionDecl* node);
    void detectOptimizedVars(FunctionDecl* node);
    bool isExecutableInstruction(const string& instruction);

public:
    CodeGen();
    void setDebugGen(DebugGen* dg);
    void setSourceLine(int line);
    void setSourceCode(const string& code);
    string getSourceLineCode(int line);
    string getOutput();
    void generate(Program* program);
    void visitIntLiteral(IntLiteral* node) override;
    void visitFloatLiteral(FloatLiteral* node) override;
    void visitLongLiteral(LongLiteral* node) override;
    void visitStringLiteral(StringLiteral* node) override;
    void visitVariable(Variable* node) override;
    void visitBinaryOp(BinaryOp* node) override;
    void visitUnaryOp(UnaryOp* node) override;
    void visitCastExpr(CastExpr* node) override;
    void visitTernaryExpr(TernaryExpr* node) override;
    void visitCallExpr(CallExpr* node) override;
    void visitArrayAccess(ArrayAccess* node) override;
    void visitAssignExpr(AssignExpr* node) override;
    void visitVarDecl(VarDecl* node) override;
    void visitAssignStmt(AssignStmt* node) override;
    void visitBlock(Block* node) override;
    void visitIfStmt(IfStmt* node) override;
    void visitWhileStmt(WhileStmt* node) override;
    void visitForStmt(ForStmt* node) override;
    void visitReturnStmt(ReturnStmt* node) override;
    void visitExprStmt(ExprStmt* node) override;
    void visitFunctionDecl(FunctionDecl* node) override;
};

#endif

