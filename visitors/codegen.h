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

// Información de variables locales
struct VarInfo {
    DataType type;
    int offset;  // Offset desde RBP
    bool isArray;
    vector<int> dimensions;
};

// Información de funciones
struct FunctionInfo {
    DataType returnType;
    vector<DataType> paramTypes;
    int stackSize;
};

class CodeGen : public Visitor {
private:
    stringstream output;
    
    // Tablas de símbolos
    map<string, VarInfo> localVars;     // Variables locales
    map<string, VarInfo> globalVars;    // Variables globales
    map<string, FunctionInfo> functions; // Funciones
    
    // Variables que no necesitan espacio en el stack (optimizadas a constantes)
    set<string> optimizedVars;  // Variables que fueron optimizadas y no necesitan stack
    
    // Estado actual
    string currentFunction;
    int stackOffset;
    int labelCounter;
    
    // Stack de registros para expresiones
    stack<string> regStack;
    bool lastExprWasFloat;
    
    // Debug generation (opcional)
    DebugGen* debugGen;
    int currentSourceLine;  // Línea de código fuente actual
    
    // Helpers
    string newLabel(string prefix = "L");
    void generar(string code, const string& varName = "", const string& description = "");
    void generarLabel(string label);
    
    // Gestión de registros
    string allocReg(DataType type);
    void freeReg(string reg);
    
    // Conversión de tipos
    void generarConversionTipo(DataType from, DataType to, string reg);
    
    // Gestión de stack frame
    void generarPrologoFuncion(string funcName, int stackSize);
    void generarEpilogoFuncion();
    
    // Helpers para arrays
    void generarAccesoArray(string arrayName, vector<unique_ptr<Expr>>& indices);
    int calculateArrayOffset(vector<int>& dimensions, int dimIndex);
    
    // Helper para calcular tamaño del stack sin generar código
    int calculateStackSize(FunctionDecl* node);
    
    // Helper para detectar variables optimizadas que no necesitan stack space
    void detectOptimizedVars(FunctionDecl* node);

public:
    CodeGen();
    
    // Configurar debug generation
    void setDebugGen(DebugGen* dg);
    void setSourceLine(int line);
    
    string getOutput();
    void generate(Program* program);
    
    // Visitor methods - Expresiones
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
    
    // Visitor methods - Statements
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

