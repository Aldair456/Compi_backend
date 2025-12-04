#include "codegen.h"
#include <iostream>
#include <set>
#include <functional>

CodeGen::CodeGen() : stackOffset(0), labelCounter(0), lastExprWasFloat(false),
                      debugGen(nullptr), currentSourceLine(0) {}

string CodeGen::getOutput() {
    return output.str();
}

string CodeGen::newLabel(string prefix) {
    return prefix + to_string(labelCounter++);
}

void CodeGen::setDebugGen(DebugGen* dg) {
    debugGen = dg;
}

void CodeGen::setSourceLine(int line) {
    currentSourceLine = line;
}

void CodeGen::generar(string code, const string& varName, const string& description) {
    output << "    " << code << "\n";
    int line = currentSourceLine > 0 ? currentSourceLine : 1;
    if (debugGen) {
        debugGen->logInstruction(code, line, varName, description);
    }
}

void CodeGen::generarLabel(string label) {
    output << label << ":\n";
    int line = currentSourceLine > 0 ? currentSourceLine : 0;
    if (debugGen) {
        debugGen->logInstruction(label + ":", line, "", "label");
    }
}

string CodeGen::allocReg(DataType type) {
    if (type == DataType::FLOAT) {
        lastExprWasFloat = true;
        return "xmm0";
    } else {
        lastExprWasFloat = false;
        return "rax";
    }
}

void CodeGen::freeReg(string reg) {}

void CodeGen::generarConversionTipo(DataType from, DataType to, string reg) {
    if (from == to) return;

    // INT/UNSIGNED -> FLOAT
    if ((from == DataType::INT || from == DataType::UNSIGNED_INT) && to == DataType::FLOAT) {
        generar("cvtsi2ssl %eax, %xmm0"); // Simplificación: tratamos unsigned como signed para float
    }
    // INT/UNSIGNED -> LONG
    else if ((from == DataType::INT || from == DataType::UNSIGNED_INT) && to == DataType::LONG) {
        if (from == DataType::UNSIGNED_INT) {
            // Unsigned int a Long: Zero extension (borrar parte alta)
            generar("movl %eax, %eax");
        } else {
            // Signed int a Long: Sign extension (copiar signo)
            generar("cltq");
        }
    }
    // FLOAT -> INT/LONG
    else if (from == DataType::FLOAT) {
        generar("cvttss2sil %xmm0, %eax"); // Truncate float to int
    }
}

void CodeGen::generarPrologoFuncion(string funcName, int stackSize) {
    generar("pushq %rbp");
    generar("movq %rsp, %rbp");
    if (stackSize > 0) {
        generar("subq $" + to_string(stackSize) + ", %rsp");
    }
}

void CodeGen::generarEpilogoFuncion() {
    generar("movq %rbp, %rsp");
    generar("popq %rbp");
    generar("ret");
}

int CodeGen::calculateArrayOffset(vector<int>& dimensions, int dimIndex) {
    int offset = 1;
    for (size_t i = dimIndex + 1; i < dimensions.size(); i++) {
        offset *= dimensions[i];
    }
    return offset;
}

void CodeGen::generate(Program* program) {
    output << ".section .data\n";
    output << "    fmt_int: .string \"%d\\n\"\n";
    output << "    fmt_float: .string \"%.2f\\n\"\n";
    output << "    fmt_long: .string \"%ld\\n\"\n";
    output << ".section .bss\n\n";
    output << ".section .text\n";
    output << "    .extern printf\n";
    output << "    .global main\n\n";

    for (auto& stmt : program->statements) {
        stmt->accept(this);
    }
    output << ".section .note.GNU-stack,\"\",@progbits\n";
}

// ========== EXPRESIONES ==========

void CodeGen::visitIntLiteral(IntLiteral* node) {
    setSourceLine(node->line);
    generar("movl $" + to_string(node->value) + ", %eax");
    lastExprWasFloat = false;
}

void CodeGen::visitFloatLiteral(FloatLiteral* node) {
    setSourceLine(node->line);
    string label = newLabel("float_const_");
    string currentOutput = output.str();
    size_t dataPos = currentOutput.find(".section .data\n");
    if (dataPos != string::npos) {
        size_t insertPos = currentOutput.find("\n", dataPos + 15) + 1;
        string decl = "    " + label + ": .float " + to_string(node->value) + "\n";
        currentOutput.insert(insertPos, decl);
        output.str("");
        output << currentOutput;
    }
    generar("movss " + label + "(%rip), %xmm0");
    lastExprWasFloat = true;
}

void CodeGen::visitLongLiteral(LongLiteral* node) {
    setSourceLine(node->line);
    generar("xorq %rax, %rax");
    generar("movq $" + to_string(node->value) + ", %rax");
    lastExprWasFloat = false;
}

void CodeGen::visitStringLiteral(StringLiteral* node) {
    setSourceLine(node->line);
    string label = newLabel("str_const_");
    string currentOutput = output.str();
    size_t dataPos = currentOutput.find(".section .data\n");
    if (dataPos != string::npos) {
        size_t insertPos = currentOutput.find("\n", dataPos + 15) + 1;
        string escaped = node->value;
        string nasmStr = "";
        for (size_t i = 0; i < escaped.length(); i++) {
            if (escaped[i] == '\\' && i + 1 < escaped.length()) {
                if (escaped[i+1] == 'n') { nasmStr += "\\n"; i++; }
                else if (escaped[i+1] == 't') { nasmStr += "\\t"; i++; }
                else if (escaped[i+1] == '"') { nasmStr += "\\\""; i++; }
                else { nasmStr += escaped[i]; }
            } else {
                nasmStr += escaped[i];
            }
        }
        string dbLine = "    " + label + ": .string \"" + nasmStr + "\"\n";
        currentOutput.insert(insertPos, dbLine);
        output.str("");
        output << currentOutput;
    }
    generar("leaq " + label + "(%rip), %rax");
    lastExprWasFloat = false;
}

void CodeGen::visitVariable(Variable* node) {
    setSourceLine(node->line);

    if (localVars.find(node->name) != localVars.end()) {
        VarInfo& var = localVars[node->name];

        if (var.type == DataType::FLOAT) {
            generar("movss -" + to_string(var.offset) + "(%rbp), %xmm0");
            lastExprWasFloat = true;
        }
        else if (var.type == DataType::LONG) {
            generar("movq -" + to_string(var.offset) + "(%rbp), %rax");
            lastExprWasFloat = false;
        }
        else if (var.type == DataType::UNSIGNED_INT) {
            // Unsigned: Cargar y asegurar ceros en la parte alta (Zero Extension)
            // movl escribe 32 bits y automáticamente limpia los 32 superiores de RAX en x86-64
            generar("movl -" + to_string(var.offset) + "(%rbp), %eax");
            lastExprWasFloat = false;
        }
        else {
            // Int (Signed): Cargar y extender signo (Sign Extension)
            generar("movl -" + to_string(var.offset) + "(%rbp), %eax");
            generar("cltq");
            lastExprWasFloat = false;
        }
    } else if (globalVars.find(node->name) != globalVars.end()) {
        generar("movl " + node->name + "(%rip), %eax");
        generar("cltq");
        lastExprWasFloat = false;
    }
}
void CodeGen::visitAssignStmt(AssignStmt* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->line);
    int assignLine = currentSourceLine;

    if (node->isArrayAssign) {
        node->value->accept(this);
        currentSourceLine = assignLine;
        if (lastExprWasFloat) {
             generar("subq $8, %rsp");
             generar("movss %xmm0, (%rsp)");
        } else {
             generar("pushq %rax");
        }
        VarInfo* varInfo = nullptr;
        if (localVars.find(node->varName) != localVars.end()) {
            varInfo = &localVars[node->varName];
        }
        if (!varInfo) { currentSourceLine = savedLine; return; }

        if (node->indices.size() >= 1) {
             node->indices[0]->accept(this);
             currentSourceLine = assignLine;
             if (node->indices.size() == 2) {
                 generar("imulq $" + to_string(varInfo->dimensions[1]) + ", %rax");
                 generar("pushq %rax");
                 node->indices[1]->accept(this);
                 currentSourceLine = assignLine;
                 generar("popq %rbx");
                 generar("addq %rbx, %rax");
             }
             int typeSize = (varInfo->type == DataType::LONG) ? 8 : 4;
             generar("imulq $" + to_string(typeSize) + ", %rax");
             generar("movq %rbp, %rbx");
             generar("subq $" + to_string(varInfo->offset) + ", %rbx");
             generar("addq %rax, %rbx");

             if (lastExprWasFloat) {
                 generar("movss (%rsp), %xmm0");
                 generar("addq $8, %rsp");
                 generar("movss %xmm0, (%rbx)");
             } else {
                 generar("popq %rax");
                 if (varInfo->type == DataType::FLOAT) {
                     generar("cvtsi2ssl %eax, %xmm0");
                     generar("movss %xmm0, (%rbx)");
                     lastExprWasFloat = true;
                 } else if (varInfo->type == DataType::LONG) {
                     generar("cltq");
                     generar("movq %rax, (%rbx)");
                     lastExprWasFloat = false;
                 } else {
                     generar("movl %eax, (%rbx)");
                     lastExprWasFloat = false;
                 }
             }
        }
    } else {
        node->value->accept(this);
        currentSourceLine = assignLine;

        if (localVars.find(node->varName) != localVars.end()) {
            VarInfo& var = localVars[node->varName];
            if (var.type == DataType::FLOAT) {
                if (!lastExprWasFloat) generar("cvtsi2ssl %eax, %xmm0");
                generar("movss %xmm0, -" + to_string(var.offset) + "(%rbp)");
                lastExprWasFloat = true;
            } else {
                if (lastExprWasFloat) generar("cvttss2sil %xmm0, %eax");
                if (var.type == DataType::LONG) {
                    if (!lastExprWasFloat) generar("cltq");
                    generar("movq %rax, -" + to_string(var.offset) + "(%rbp)");
                } else {
                    generar("movl %eax, -" + to_string(var.offset) + "(%rbp)");
                }
                lastExprWasFloat = false;
            }
        }
    }
    currentSourceLine = savedLine;
}

void CodeGen::visitBinaryOp(BinaryOp* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->op.line);
    int opLine = currentSourceLine;

    // Detectar si la operación es Unsigned
    bool isUnsignedOp = (node->left->inferredType == DataType::UNSIGNED_INT ||
                         node->right->inferredType == DataType::UNSIGNED_INT);
    
    // Detectar si es Long
    DataType resultType = node->inferredType;
    bool isLongOp = (resultType == DataType::LONG);

    node->right->accept(this);
    bool rightWasFloat = lastExprWasFloat;

    currentSourceLine = opLine;
    if (rightWasFloat) {
        generar("subq $8, %rsp");
        generar("movss %xmm0, (%rsp)");
    } else {
        generar("pushq %rax");
    }

    node->left->accept(this);
    bool leftWasFloat = lastExprWasFloat;
    bool isFloatOp = leftWasFloat || rightWasFloat;

    currentSourceLine = opLine;
    if (rightWasFloat) {
        generar("movss (%rsp), %xmm1");
        generar("addq $8, %rsp");
    } else {
        generar("popq %rbx");
    }

    // Promociones Implícitas
    if (isFloatOp && !leftWasFloat)  generar("cvtsi2ssl %eax, %xmm0");
    if (isFloatOp && !rightWasFloat) generar("cvtsi2ssl %ebx, %xmm1");

    currentSourceLine = opLine;
    switch (node->op.type) {
        case TokenType::PLUS:
            if (isFloatOp) { generar("addss %xmm1, %xmm0"); lastExprWasFloat = true; }
            else if (isLongOp) { generar("addq %rbx, %rax"); lastExprWasFloat = false; }
            else           { generar("addl %ebx, %eax");    lastExprWasFloat = false; }
            break;

        case TokenType::MINUS:
            if (isFloatOp) { generar("subss %xmm1, %xmm0"); lastExprWasFloat = true; }
            else if (isLongOp) { generar("subq %rbx, %rax"); lastExprWasFloat = false; }
            else           { generar("subl %ebx, %eax");    lastExprWasFloat = false; }
            break;

        case TokenType::MULTIPLY:
            if (isFloatOp) { generar("mulss %xmm1, %xmm0"); lastExprWasFloat = true; }
            else if (isLongOp) { generar("imulq %rbx, %rax"); lastExprWasFloat = false; }
            else           { generar("imull %ebx, %eax");   lastExprWasFloat = false; }
            break;

        case TokenType::DIVIDE:
            if (isFloatOp) {
                generar("divss %xmm1, %xmm0");
                lastExprWasFloat = true;
            } else {
                generar("xorq %rdx, %rdx");
                if (isLongOp) {
                    generar("cqto");
                    generar("idivq %rbx");
                } else if (isUnsignedOp) {
                    generar("divl %ebx");
                } else {
                    generar("cltd");
                    generar("idivl %ebx");
                }
                lastExprWasFloat = false;
            }
            break;
        
        case TokenType::MODULO:
             generar("xorq %rdx, %rdx");
             if (isLongOp) { generar("cqto"); generar("idivq %rbx"); generar("movq %rdx, %rax"); }
             else if (isUnsignedOp) { generar("divl %ebx"); generar("movl %edx, %eax"); }
             else { generar("cltd"); generar("idivl %ebx"); generar("movl %edx, %eax"); }
             lastExprWasFloat = false;
             break;

        case TokenType::EQ:
            if (isFloatOp) { generar("ucomiss %xmm1, %xmm0"); generar("setnp %al"); generar("movb %al, %ah"); generar("setz %al"); generar("andb %ah, %al"); }
            else if (isLongOp) { generar("cmpq %rbx, %rax"); generar("sete %al"); }
            else { generar("cmpl %ebx, %eax"); generar("sete %al"); }
            generar("movzbq %al, %rax"); lastExprWasFloat = false; break;

        case TokenType::NE:
            if (isFloatOp) { generar("ucomiss %xmm1, %xmm0"); generar("setnz %al"); }
            else if (isLongOp) { generar("cmpq %rbx, %rax"); generar("setne %al"); }
            else { generar("cmpl %ebx, %eax"); generar("setne %al"); }
            generar("movzbq %al, %rax"); lastExprWasFloat = false; break;

        case TokenType::LT:
            if (isFloatOp) { generar("ucomiss %xmm1, %xmm0"); generar("setb %al"); }
            else {
                if (isLongOp) generar("cmpq %rbx, %rax");
                else          generar("cmpl %ebx, %eax");
                if (isUnsignedOp) generar("setb %al");
                else              generar("setl %al");
            }
            generar("movzbq %al, %rax"); lastExprWasFloat = false; break;

        case TokenType::GT:
            if (isFloatOp) { generar("ucomiss %xmm1, %xmm0"); generar("seta %al"); }
            else {
                if (isLongOp) generar("cmpq %rbx, %rax");
                else          generar("cmpl %ebx, %eax");
                if (isUnsignedOp) generar("seta %al");
                else              generar("setg %al");
            }
            generar("movzbq %al, %rax"); lastExprWasFloat = false; break;

        case TokenType::LE:
            if (isFloatOp) { generar("ucomiss %xmm1, %xmm0"); generar("setbe %al"); }
            else {
                if (isLongOp) generar("cmpq %rbx, %rax");
                else          generar("cmpl %ebx, %eax");
                if (isUnsignedOp) generar("setbe %al");
                else              generar("setle %al");
            }
            generar("movzbq %al, %rax"); lastExprWasFloat = false; break;

        case TokenType::GE:
            if (isFloatOp) { generar("ucomiss %xmm1, %xmm0"); generar("setae %al"); }
            else {
                if (isLongOp) generar("cmpq %rbx, %rax");
                else          generar("cmpl %ebx, %eax");
                if (isUnsignedOp) generar("setae %al");
                else              generar("setge %al");
            }
            generar("movzbq %al, %rax"); lastExprWasFloat = false; break;

        default: break;
    }
    currentSourceLine = savedLine;
}

void CodeGen::visitUnaryOp(UnaryOp* node) {
    setSourceLine(node->op.line);
    node->operand->accept(this);
    if (node->op.type == TokenType::MINUS) {
        if (lastExprWasFloat) {
            generar("movss %xmm0, %xmm1"); generar("xorps %xmm0, %xmm0"); generar("subss %xmm1, %xmm0");
        } else { generar("negq %rax"); }
    } else if (node->op.type == TokenType::NOT) {
        generar("testq %rax, %rax"); generar("setz %al"); generar("movzbq %al, %rax");
    }
}

void CodeGen::visitCastExpr(CastExpr* node) {
    setSourceLine(node->line);
    node->expr->accept(this);
    DataType fromType = node->expr->inferredType;
    DataType toType = node->targetType;
    if (fromType != toType) {
        if (fromType == DataType::INT && toType == DataType::FLOAT) { generar("cvtsi2ssl %eax, %xmm0"); lastExprWasFloat = true; }
        else if (fromType == DataType::FLOAT && toType == DataType::INT) { generar("cvttss2sil %xmm0, %eax"); lastExprWasFloat = false; }
        else if (fromType == DataType::INT && toType == DataType::LONG) { generar("cltq"); lastExprWasFloat = false; }
    }
}

void CodeGen::visitTernaryExpr(TernaryExpr* node) {
    setSourceLine(node->line);
    string labelFalse = newLabel("ternary_false_");
    string labelEnd = newLabel("ternary_end_");
    node->condition->accept(this);
    generar("testq %rax, %rax");
    generar("jz " + labelFalse);
    node->exprTrue->accept(this);
    generar("jmp " + labelEnd);
    generarLabel(labelFalse);
    node->exprFalse->accept(this);
    generarLabel(labelEnd);
}

void CodeGen::visitCallExpr(CallExpr* node) {
    setSourceLine(node->line);
    if (node->functionName == "printf") {
        if (node->arguments.size() > 0) {
            StringLiteral* fmtStr = dynamic_cast<StringLiteral*>(node->arguments[0].get());
            if (fmtStr) {
                fmtStr->accept(this);
                generar("movq %rax, %rdi");
                if (node->arguments.size() > 1) {
                    generar("pushq %rdi");
                    node->arguments[1]->accept(this);
                    if (lastExprWasFloat) { generar("cvtss2sd %xmm0, %xmm0"); generar("popq %rdi"); generar("movq $1, %rax"); }
                    else { generar("movq %rax, %rsi"); generar("popq %rdi"); generar("xorq %rax, %rax"); }
                } else { generar("xorq %rax, %rax"); }
            } else {
                node->arguments[0]->accept(this);
                if (lastExprWasFloat) { generar("cvtss2sd %xmm0, %xmm0"); generar("leaq fmt_float(%rip), %rdi"); generar("movq $1, %rax"); }
                else { generar("movq %rax, %rsi"); generar("leaq fmt_int(%rip), %rdi"); generar("xorq %rax, %rax"); }
            }
            generar("call printf@PLT");
            lastExprWasFloat = false;
        }
    } else {
        vector<string> argRegs = {"%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"};
        for (size_t i = 0; i < node->arguments.size() && i < 6; i++) {
            node->arguments[i]->accept(this);
            generar("movq %rax, " + argRegs[i]);
        }
        generar("call " + node->functionName);
        if (functions.count(node->functionName)) {
            if (functions[node->functionName].returnType == DataType::FLOAT) {
                lastExprWasFloat = true;
            } else {
                lastExprWasFloat = false;
            }
        } else {
            lastExprWasFloat = false;
        }
    }
}

void CodeGen::visitArrayAccess(ArrayAccess* node) {
    setSourceLine(node->line);
    VarInfo* varInfo = nullptr;
    if (localVars.find(node->arrayName) != localVars.end()) varInfo = &localVars[node->arrayName];
    else if (globalVars.find(node->arrayName) != globalVars.end()) varInfo = &globalVars[node->arrayName];
    if (!varInfo || !varInfo->isArray) return;

    if (node->indices.size() >= 1) {
        node->indices[0]->accept(this);
        if (node->indices.size() == 2) {
            generar("imulq $" + to_string(varInfo->dimensions[1]) + ", %rax");
            generar("pushq %rax");
            node->indices[1]->accept(this);
            generar("popq %rbx");
            generar("addq %rbx, %rax");
        }
        int typeSize = (varInfo->type == DataType::LONG) ? 8 : 4;
        generar("imulq $" + to_string(typeSize) + ", %rax");
        generar("movq %rbp, %rbx");
        generar("subq $" + to_string(varInfo->offset) + ", %rbx");
        generar("addq %rax, %rbx");
        if (varInfo->type == DataType::FLOAT) {
            generar("movss (%rbx), %xmm0");
            lastExprWasFloat = true;
        } else {
            generar("movl (%rbx), %eax");
            generar("cltq");
            lastExprWasFloat = false;
        }
    }
}

void CodeGen::visitAssignExpr(AssignExpr* node) {
    setSourceLine(node->line);
    if (node->isArrayAssign) {
        node->value->accept(this);
        if (lastExprWasFloat) { generar("subq $8, %rsp"); generar("movss %xmm0, (%rsp)"); }
        else { generar("pushq %rax"); }
        VarInfo* varInfo = nullptr;
        if (localVars.find(node->varName) != localVars.end()) varInfo = &localVars[node->varName];
        if (!varInfo) return;
        if (node->indices.size() >= 1) {
             node->indices[0]->accept(this);
             if (node->indices.size() == 2) {
                 generar("imulq $" + to_string(varInfo->dimensions[1]) + ", %rax");
                 generar("pushq %rax");
                 node->indices[1]->accept(this);
                 generar("popq %rbx");
                 generar("addq %rbx, %rax");
             }
             int typeSize = (varInfo->type == DataType::LONG) ? 8 : 4;
             generar("imulq $" + to_string(typeSize) + ", %rax");
             generar("movq %rbp, %rbx");
             generar("subq $" + to_string(varInfo->offset) + ", %rbx");
             generar("addq %rax, %rbx");
             if (lastExprWasFloat) {
                 generar("movss (%rsp), %xmm0");
                 generar("addq $8, %rsp");
                 generar("movss %xmm0, (%rbx)");
             } else {
                 generar("popq %rax");
                 if (varInfo->type == DataType::FLOAT) { generar("cvtsi2ssl %eax, %xmm0"); generar("movss %xmm0, (%rbx)"); lastExprWasFloat = true; }
                 else if (varInfo->type == DataType::LONG) { generar("cltq"); generar("movq %rax, (%rbx)"); lastExprWasFloat = false; }
                 else { generar("movl %eax, (%rbx)"); lastExprWasFloat = false; }
             }
        }
    } else {
        node->value->accept(this);
        if (localVars.find(node->varName) != localVars.end()) {
            VarInfo& var = localVars[node->varName];
            if (var.type == DataType::FLOAT) {
                if (!lastExprWasFloat) generar("cvtsi2ssl %eax, %xmm0");
                generar("movss %xmm0, -" + to_string(var.offset) + "(%rbp)");
                lastExprWasFloat = true;
            } else {
                if (lastExprWasFloat) generar("cvttss2sil %xmm0, %eax");
                if (var.type == DataType::LONG) {
                    if (!lastExprWasFloat) generar("cltq");
                    generar("movq %rax, -" + to_string(var.offset) + "(%rbp)");
                } else {
                    generar("movl %eax, -" + to_string(var.offset) + "(%rbp)");
                }
                lastExprWasFloat = false;
            }
        }
    }
}

void CodeGen::visitVarDecl(VarDecl* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->line);
    if (currentFunction.empty()) return;
    if (optimizedVars.find(node->name) != optimizedVars.end()) {
        VarInfo varInfo; varInfo.type = node->type; varInfo.offset = 0; varInfo.isArray = node->isArray; varInfo.dimensions = node->dimensions;
        localVars[node->name] = varInfo; currentSourceLine = savedLine; return;
    }
    int size = (node->type == DataType::LONG) ? 8 : 4;
    if (node->isArray) {
        int totalSize = size;
        for (int dim : node->dimensions) totalSize *= dim;
        stackOffset += totalSize;
    } else { stackOffset += size; }
    VarInfo varInfo; varInfo.type = node->type; varInfo.offset = stackOffset; varInfo.isArray = node->isArray; varInfo.dimensions = node->dimensions;
    localVars[node->name] = varInfo;
    if (debugGen) {
        string typeStr = (node->type == DataType::FLOAT) ? "float" : "int";
        debugGen->logStackVariable(node->name, stackOffset, typeStr, node->isArray, node->line);
    }
    if (node->initializer) {
        int declLine = currentSourceLine;
        node->initializer->accept(this);
        currentSourceLine = declLine;
        if (node->type == DataType::FLOAT) {
            if (!lastExprWasFloat) generar("cvtsi2ssl %eax, %xmm0");
            generar("movss %xmm0, -" + to_string(stackOffset) + "(%rbp)");
            lastExprWasFloat = true;
        } else if (node->type == DataType::LONG) {
            if (lastExprWasFloat) generar("cvttss2sil %xmm0, %eax");
            generar("cltq");
            generar("movq %rax, -" + to_string(stackOffset) + "(%rbp)");
            lastExprWasFloat = false;
        } else {
            if (lastExprWasFloat) generar("cvttss2sil %xmm0, %eax");
            generar("movl %eax, -" + to_string(stackOffset) + "(%rbp)");
            lastExprWasFloat = false;
        }
    }
    currentSourceLine = savedLine;
}

void CodeGen::visitBlock(Block* node) {
    for (auto& stmt : node->statements) stmt->accept(this);
}

void CodeGen::visitIfStmt(IfStmt* node) {
    setSourceLine(node->line);
    string labelElse = newLabel("else_");
    string labelEnd = newLabel("endif_");
    node->condition->accept(this);
    generar("testq %rax, %rax");
    if (node->elseBranch) {
        generar("jz " + labelElse);
        node->thenBranch->accept(this);
        generar("jmp " + labelEnd);
        generarLabel(labelElse);
        node->elseBranch->accept(this);
        generarLabel(labelEnd);
    } else {
        generar("jz " + labelEnd);
        node->thenBranch->accept(this);
        generarLabel(labelEnd);
    }
}

void CodeGen::visitWhileStmt(WhileStmt* node) {
    setSourceLine(node->line);
    string labelStart = newLabel("while_start_");
    string labelEnd = newLabel("while_end_");
    generarLabel(labelStart);
    node->condition->accept(this);
    generar("testq %rax, %rax");
    generar("jz " + labelEnd);
    node->body->accept(this);
    generar("jmp " + labelStart);
    generarLabel(labelEnd);
}

void CodeGen::visitForStmt(ForStmt* node) {
    setSourceLine(node->line);
    string labelStart = newLabel("for_start_");
    string labelEnd = newLabel("for_end_");
    if (node->initializer) node->initializer->accept(this);
    generarLabel(labelStart);
    if (node->condition) {
        node->condition->accept(this);
        generar("testq %rax, %rax");
        generar("jz " + labelEnd);
    }
    node->body->accept(this);
    if (node->increment) node->increment->accept(this);
    generar("jmp " + labelStart);
    generarLabel(labelEnd);
}

void CodeGen::visitReturnStmt(ReturnStmt* node) {
    setSourceLine(node->line);
    if (node->value) node->value->accept(this);
    generar("jmp .end_" + currentFunction);
}

void CodeGen::visitExprStmt(ExprStmt* node) {
    setSourceLine(node->line);
    node->expression->accept(this);
}

// Helpers
// *** CORRECCIÓN CRÍTICA: ANÁLISIS DE EXPRESIONES (AGREGADO) ***
void CodeGen::detectOptimizedVars(FunctionDecl* node) {
    optimizedVars.clear();
    set<string> declaredVars;
    set<string> usedVars;

    // Helper recursivo para explorar expresiones
    function<void(Expr*)> analyzeExpr = [&](Expr* expr) {
        if (!expr) return;
        if (Variable* var = dynamic_cast<Variable*>(expr)) {
            usedVars.insert(var->name); // ¡Encontrado uso de variable!
        }
        else if (BinaryOp* bin = dynamic_cast<BinaryOp*>(expr)) {
            analyzeExpr(bin->left.get());
            analyzeExpr(bin->right.get());
        }
        else if (UnaryOp* un = dynamic_cast<UnaryOp*>(expr)) {
            analyzeExpr(un->operand.get());
        }
        else if (CallExpr* call = dynamic_cast<CallExpr*>(expr)) {
            for (auto& arg : call->arguments) analyzeExpr(arg.get());
        }
        else if (CastExpr* cast = dynamic_cast<CastExpr*>(expr)) {
            analyzeExpr(cast->expr.get());
        }
        else if (AssignExpr* assign = dynamic_cast<AssignExpr*>(expr)) {
            usedVars.insert(assign->varName);
            analyzeExpr(assign->value.get());
            for(auto& idx : assign->indices) analyzeExpr(idx.get());
        }
        else if (ArrayAccess* arr = dynamic_cast<ArrayAccess*>(expr)) {
            usedVars.insert(arr->arrayName);
            for(auto& idx : arr->indices) analyzeExpr(idx.get());
        }
        else if (TernaryExpr* ter = dynamic_cast<TernaryExpr*>(expr)) {
            analyzeExpr(ter->condition.get());
            analyzeExpr(ter->exprTrue.get());
            analyzeExpr(ter->exprFalse.get());
        }
    };

    function<void(Stmt*)> analyzeStmt = [&](Stmt* stmt) {
        if (!stmt) return;
        if (VarDecl* varDecl = dynamic_cast<VarDecl*>(stmt)) {
            declaredVars.insert(varDecl->name);
            if (varDecl->initializer) analyzeExpr(varDecl->initializer.get());
        }
        if (ReturnStmt* ret = dynamic_cast<ReturnStmt*>(stmt)) {
            if (ret->value) analyzeExpr(ret->value.get());
        }
        if (AssignStmt* assign = dynamic_cast<AssignStmt*>(stmt)) {
            usedVars.insert(assign->varName);
            analyzeExpr(assign->value.get());
            for(auto& idx : assign->indices) analyzeExpr(idx.get());
        }
        if (ExprStmt* exprS = dynamic_cast<ExprStmt*>(stmt)) {
            analyzeExpr(exprS->expression.get());
        }
        if (Block* block = dynamic_cast<Block*>(stmt)) {
            for (auto& s : block->statements) analyzeStmt(s.get());
        }
        if (IfStmt* ifStmt = dynamic_cast<IfStmt*>(stmt)) {
            analyzeExpr(ifStmt->condition.get());
            analyzeStmt(ifStmt->thenBranch.get());
            if (ifStmt->elseBranch) analyzeStmt(ifStmt->elseBranch.get());
        }
        if (WhileStmt* whileStmt = dynamic_cast<WhileStmt*>(stmt)) {
            analyzeExpr(whileStmt->condition.get());
            analyzeStmt(whileStmt->body.get());
        }
        if (ForStmt* forStmt = dynamic_cast<ForStmt*>(stmt)) {
            if (forStmt->initializer) analyzeStmt(forStmt->initializer.get());
            if (forStmt->condition) analyzeExpr(forStmt->condition.get());
            if (forStmt->increment) analyzeExpr(forStmt->increment.get());
            analyzeStmt(forStmt->body.get());
        }
    };
    analyzeStmt(node->body.get());
    for (const string& var : declaredVars) if (usedVars.find(var) == usedVars.end()) optimizedVars.insert(var);
}

int CodeGen::calculateStackSize(FunctionDecl* node) {
    int savedStackOffset = stackOffset;
    map<string, VarInfo> savedLocalVars = localVars;
    set<string> savedOptimizedVars = optimizedVars;
    stringstream savedOutput;
    savedOutput << output.str();
    int savedSourceLine = currentSourceLine;
    DebugGen* savedDebugGen = debugGen;
    detectOptimizedVars(node);
    stackOffset = 0; localVars.clear(); output.str(""); debugGen = nullptr;
    for (size_t i = 0; i < node->parameters.size() && i < 6; i++) {
        int size = (node->parameters[i].first == DataType::LONG) ? 8 : 4;
        stackOffset += size;
        VarInfo varInfo; varInfo.type = node->parameters[i].first; varInfo.offset = stackOffset; localVars[node->parameters[i].second] = varInfo;
    }
    node->body->accept(this);
    int totalStackSize = stackOffset;
    stackOffset = savedStackOffset; localVars = savedLocalVars; optimizedVars = savedOptimizedVars;
    output.str(""); output << savedOutput.str(); currentSourceLine = savedSourceLine; debugGen = savedDebugGen;
    return totalStackSize;
}

void CodeGen::visitFunctionDecl(FunctionDecl* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->line);
    int funcLine = currentSourceLine;
    currentFunction = node->name;
    localVars.clear();
    stackOffset = 0;
    FunctionInfo funcInfo;
    funcInfo.returnType = node->returnType;
    for (auto& param : node->parameters) funcInfo.paramTypes.push_back(param.first);
    functions[node->name] = funcInfo;

    // CORRECCIÓN STACK (FIBONACCI -1 FIX)
    int totalStackSize = calculateStackSize(node);
    int stackToReserve = totalStackSize;
    if (stackToReserve > 0 && stackToReserve % 16 != 0) stackToReserve = ((stackToReserve / 16) + 1) * 16;

    generarLabel(node->name);
    currentSourceLine = funcLine;
    generar("pushq %rbp");
    generar("movq %rsp, %rbp");
    if (stackToReserve > 0) generar("subq $" + to_string(stackToReserve) + ", %rsp");

    vector<string> paramRegs = {"%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"};
    vector<string> paramRegs32 = {"%edi", "%esi", "%edx", "%ecx", "%r8d", "%r9d"};
    for (size_t i = 0; i < node->parameters.size() && i < 6; i++) {
        auto& param = node->parameters[i];
        int size = (param.first == DataType::LONG) ? 8 : 4;
        stackOffset += size;
        VarInfo varInfo; varInfo.type = param.first; varInfo.offset = stackOffset; varInfo.isArray = false;
        localVars[param.second] = varInfo;
        if (debugGen) debugGen->logStackVariable(param.second, stackOffset, "param", false, node->line);
        currentSourceLine = funcLine;
        if (param.first == DataType::LONG) generar("movq " + paramRegs[i] + ", -" + to_string(varInfo.offset) + "(%rbp)");
        else generar("movl " + paramRegs32[i] + ", -" + to_string(varInfo.offset) + "(%rbp)");
    }
    node->body->accept(this);
    generarLabel(".end_" + node->name);
    generar("leave");
    generar("ret");
    output << "\n";
    currentFunction = "";
    currentSourceLine = savedLine;
}