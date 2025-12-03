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

void CodeGen::freeReg(string reg) {
}

void CodeGen::generarConversionTipo(DataType from, DataType to, string reg) {
    if (from == to) return;

    if (from == DataType::INT && to == DataType::FLOAT) {
        generar("cvtsi2ss xmm0, eax");
    }
    else if (from == DataType::FLOAT && to == DataType::INT) {
        generar("cvttss2si eax, xmm0");
    }
    else if (from == DataType::INT && to == DataType::LONG) {
        generar("movsx rax, eax");
    }
    else if (from == DataType::LONG && to == DataType::INT) {
    }
    else if (from == DataType::UNSIGNED_INT && to == DataType::INT) {
    }
}

void CodeGen::generarPrologoFuncion(string funcName, int stackSize) {
    generar("push rbp");
    generar("mov rbp, rsp");
    if (stackSize > 0) {
        generar("sub rsp, " + to_string(stackSize));
    }
}

void CodeGen::generarEpilogoFuncion() {
    generar("mov rsp, rbp");
    generar("pop rbp");
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
    output << "section .data\n";
    output << "    fmt_int: db \"%d\", 10, 0\n";
    output << "    fmt_float: db \"%.2f\", 10, 0\n";
    output << "    fmt_long: db \"%ld\", 10, 0\n";
    output << "\n";

    output << "section .bss\n";
    output << "\n";

    output << "section .text\n";
    output << "    extern printf\n";
    output << "    global main\n";
    output << "\n";

    for (auto& stmt : program->statements) {
        stmt->accept(this);
    }
}



void CodeGen::visitIntLiteral(IntLiteral* node) {
    setSourceLine(node->line);
    generar("mov eax, " + to_string(node->value));
    lastExprWasFloat = false;
}

void CodeGen::visitFloatLiteral(FloatLiteral* node) {
    setSourceLine(node->line);
    string label = newLabel("float_const_");

    stringstream temp;
    temp << output.str();

    string currentOutput = output.str();
    size_t dataPos = currentOutput.find("section .data\n");
    if (dataPos != string::npos) {
        size_t insertPos = currentOutput.find("\n", dataPos + 14) + 1;
        currentOutput.insert(insertPos, "    " + label + ": dd " + to_string(node->value) + "\n");
        output.str("");
        output << currentOutput;
    }

    generar("movss xmm0, [" + label + "]");
    lastExprWasFloat = true;
}

void CodeGen::visitLongLiteral(LongLiteral* node) {
    setSourceLine(node->line);
    generar("xor rax, rax");
    generar("mov eax, " + to_string(node->value));
    lastExprWasFloat = false;
}
void CodeGen::visitStringLiteral(StringLiteral* node) {
    setSourceLine(node->line);
    string label = newLabel("str_const_");

    string currentOutput = output.str();
    size_t dataPos = currentOutput.find("section .data\n");
    if (dataPos != string::npos) {
        size_t insertPos = currentOutput.find("\n", dataPos + 14) + 1;

        string escaped = node->value;
        string nasmStr = "";
        bool hasNewline = false;

        for (size_t i = 0; i < escaped.length(); i++) {
            if (escaped[i] == '\\' && i + 1 < escaped.length()) {
                if (escaped[i+1] == 'n') {
                    // Newline - lo manejamos después del string
                    hasNewline = true;
                    i++;  // Saltar el
                    continue;
                } else if (escaped[i+1] == '\\') {
                    nasmStr += "\\\\";
                    i++;  // Saltar el segundo '\'
                } else if (escaped[i+1] == '"') {
                    nasmStr += "\\\"";
                    i++;
                } else if (escaped[i+1] == 't') {
                    nasmStr += "\\t";
                    i++;
                } else {
                    nasmStr += escaped[i];
                }
            } else if (escaped[i] == '"') {
                nasmStr += "\\\"";
            } else {
                nasmStr += escaped[i];
            }
        }

        string dbLine = "    " + label + ": db \"" + nasmStr + "\"";
        if (hasNewline) {
            dbLine += ", 10";
        }
        dbLine += ", 0\n";

        currentOutput.insert(insertPos, dbLine);
        output.str("");
        output << currentOutput;
    }

    generar("lea rax, [" + label + "]");
    lastExprWasFloat = false;
}

void CodeGen::visitVariable(Variable* node) {
    setSourceLine(node->line);
    if (localVars.find(node->name) != localVars.end()) {
        VarInfo& var = localVars[node->name];

        if (var.type == DataType::FLOAT) {
            generar("movss xmm0, [rbp - " + to_string(var.offset) + "]");
            lastExprWasFloat = true;
        } else if (var.type == DataType::LONG) {
            generar("mov rax, [rbp - " + to_string(var.offset) + "]");
            lastExprWasFloat = false;
        } else {
            generar("mov eax, [rbp - " + to_string(var.offset) + "]");
            generar("movsx rax, eax");
            lastExprWasFloat = false;
        }
    } else if (globalVars.find(node->name) != globalVars.end()) {
        VarInfo& var = globalVars[node->name];
        generar("mov eax, [" + node->name + "]");

        generar("movsx rax, eax");
        lastExprWasFloat = false;
    }
}

void CodeGen::visitBinaryOp(BinaryOp* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->op.line);
    int opLine = currentSourceLine;
    node->right->accept(this);
    bool rightWasFloat = lastExprWasFloat;

    currentSourceLine = opLine;
    if (rightWasFloat) {
        generar("sub rsp, 8");
        generar("movss [rsp], xmm0");
    } else {
        generar("push rax");
    }

    node->left->accept(this);
    bool leftWasFloat = lastExprWasFloat;

    bool isFloatOp = leftWasFloat || rightWasFloat;

    currentSourceLine = opLine;
    if (rightWasFloat) {
        generar("movss xmm1, [rsp]");
        generar("add rsp, 8");
    } else {
        generar("pop rbx");
        if (isFloatOp && !rightWasFloat) {
            generar("cvtsi2ss xmm1, ebx");
        }
    }

    if (isFloatOp && !leftWasFloat) {
        generar("cvtsi2ss xmm0, eax");
    }

    currentSourceLine = opLine;
    switch (node->op.type) {
        case TokenType::PLUS:
            if (isFloatOp) {
                generar("addss xmm0, xmm1");
                lastExprWasFloat = true;
            } else {
                generar("add rax, rbx");
                lastExprWasFloat = false;
            }
            break;

        case TokenType::MINUS:
            if (isFloatOp) {
                generar("subss xmm0, xmm1");
                lastExprWasFloat = true;
            } else {
                generar("sub rax, rbx");
                lastExprWasFloat = false;
            }
            break;

        case TokenType::MULTIPLY:
            if (isFloatOp) {
                generar("mulss xmm0, xmm1");
                lastExprWasFloat = true;
            } else {
                generar("imul rax, rbx");
                lastExprWasFloat = false;
            }
            break;

        case TokenType::DIVIDE:
            if (isFloatOp) {
                generar("divss xmm0, xmm1");
                lastExprWasFloat = true;
            } else {
                generar("xor rdx, rdx");
                generar("idiv rbx");
                lastExprWasFloat = false;
            }
            break;

        case TokenType::EQ:
            generar("cmp rax, rbx");
            generar("sete al");
            generar("movzx eax, al");
            lastExprWasFloat = false;
            break;

        case TokenType::NE:
            generar("cmp rax, rbx");
            generar("setne al");
            generar("movzx eax, al");
            lastExprWasFloat = false;
            break;

        case TokenType::LT:
            generar("cmp rax, rbx");
            generar("setl al");
            generar("movzx eax, al");
            lastExprWasFloat = false;
            break;

        case TokenType::GT:
            generar("cmp rax, rbx");
            generar("setg al");
            generar("movzx eax, al");
            lastExprWasFloat = false;
            break;

        case TokenType::LE:
            generar("cmp rax, rbx");
            generar("setle al");
            generar("movzx eax, al");
            lastExprWasFloat = false;
            break;

        case TokenType::GE:
            generar("cmp rax, rbx");
            generar("setge al");
            generar("movzx eax, al");
            lastExprWasFloat = false;
            break;

        default:
            break;
    }
    currentSourceLine = savedLine;
}

void CodeGen::visitUnaryOp(UnaryOp* node) {
    setSourceLine(node->op.line);
    node->operand->accept(this);

    if (node->op.type == TokenType::MINUS) {
        if (lastExprWasFloat) {
            generar("movss xmm1, xmm0");
            generar("xorps xmm0, xmm0");
            generar("subss xmm0, xmm1");
        } else {
            generar("neg rax");
        }
    } else if (node->op.type == TokenType::NOT) {
        generar("test rax, rax");
        generar("setz al");
        generar("movzx eax, al");
    }
}

void CodeGen::visitCastExpr(CastExpr* node) {
    setSourceLine(node->line);
    node->expr->accept(this);

    DataType fromType = node->expr->inferredType;
    DataType toType = node->targetType;

    if (fromType != toType) {
        if (fromType == DataType::INT && toType == DataType::FLOAT) {
            generar("cvtsi2ss xmm0, eax");
            lastExprWasFloat = true;
        } else if (fromType == DataType::FLOAT && toType == DataType::INT) {
            generar("cvttss2si eax, xmm0");
            lastExprWasFloat = false;
        } else if (fromType == DataType::INT && toType == DataType::LONG) {
            generar("movsx rax, eax");
            lastExprWasFloat = false;
        }
    }
}

void CodeGen::visitTernaryExpr(TernaryExpr* node) {
    setSourceLine(node->line);
    string labelFalse = newLabel("ternary_false_");
    string labelEnd = newLabel("ternary_end_");

    node->condition->accept(this);
    generar("test rax, rax");
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
                generar("mov rdi, rax");

                if (node->arguments.size() > 1) {
                    generar("push rdi");

                    node->arguments[1]->accept(this);

                    if (lastExprWasFloat) {
                        generar("cvtss2sd xmm0, xmm0");
                        generar("pop rdi");
                        generar("mov rax, 1");
                    } else {
                        generar("mov rsi, rax");
                        generar("pop rdi");
                        generar("xor rax, rax");
                    }
                } else {
                    generar("xor rax, rax");
                }
            } else {
                node->arguments[0]->accept(this);

                if (lastExprWasFloat) {
                    generar("cvtss2sd xmm0, xmm0");
                    generar("lea rdi, [fmt_float]");
                    generar("mov rax, 1");
                } else {
                    generar("mov rsi, rax");
                    generar("lea rdi, [fmt_int]");
                    generar("xor rax, rax");
                }
            }

            generar("call printf");

        }
    } else {

        vector<string> argRegs = {"rdi", "rsi", "rdx", "rcx", "r8", "r9"};

        for (size_t i = 0; i < node->arguments.size() && i < 6; i++) {
            node->arguments[i]->accept(this);
            generar("mov " + argRegs[i] + ", rax");
        }

        generar("call " + node->functionName);
    }
}

void CodeGen::visitArrayAccess(ArrayAccess* node) {
    setSourceLine(node->line);
    VarInfo* varInfo = nullptr;

    if (localVars.find(node->arrayName) != localVars.end()) {
        varInfo = &localVars[node->arrayName];
    } else if (globalVars.find(node->arrayName) != globalVars.end()) {
        varInfo = &globalVars[node->arrayName];
    }

    if (!varInfo || !varInfo->isArray) {
        cerr << "Error: " << node->arrayName << " is not an array" << endl;
        return;
    }


    if (node->indices.size() == 1) {
        node->indices[0]->accept(this);

        int typeSize = 4;
        if (varInfo->type == DataType::LONG) typeSize = 8;

        generar("imul rax, " + to_string(typeSize));
        generar("mov rbx, rbp");
        generar("sub rbx, " + to_string(varInfo->offset));
        generar("add rbx, rax");

        if (varInfo->type == DataType::FLOAT) {
            generar("movss xmm0, [rbx]");
            lastExprWasFloat = true;
        } else {
            generar("mov eax, [rbx]");
            generar("movsx rax, eax");
            lastExprWasFloat = false;
        }
    } else if (node->indices.size() == 2) {

        node->indices[0]->accept(this);
        generar("imul rax, " + to_string(varInfo->dimensions[1]));
        generar("push rax");

        node->indices[1]->accept(this);
        generar("pop rbx");
        generar("add rax, rbx");

        int typeSize = 4;
        if (varInfo->type == DataType::LONG) typeSize = 8;

        generar("imul rax, " + to_string(typeSize));
        generar("mov rbx, rbp");
        generar("sub rbx, " + to_string(varInfo->offset));
        generar("add rbx, rax");

        if (varInfo->type == DataType::FLOAT) {
            generar("movss xmm0, [rbx]");
            lastExprWasFloat = true;
        } else {
            generar("mov eax, [rbx]");
            lastExprWasFloat = false;
        }
    }
}

void CodeGen::visitAssignExpr(AssignExpr* node) {
    setSourceLine(node->line);
    if (node->isArrayAssign) {
        node->value->accept(this);
        bool wasFloat = lastExprWasFloat;
        if (wasFloat) {
            generar("sub rsp, 8");
            generar("movss [rsp], xmm0");
        } else {
            generar("push rax");
        }
        VarInfo* varInfo = nullptr;
        if (localVars.find(node->varName) != localVars.end()) {
            varInfo = &localVars[node->varName];
        }
        if (!varInfo) {
            generar("add rsp, 8");
            return;
        }
        if (node->indices.size() == 1) {
            node->indices[0]->accept(this);
            int typeSize = 4;
            if (varInfo->type == DataType::LONG) typeSize = 8;
            generar("imul rax, " + to_string(typeSize));
            generar("mov rbx, rbp");
            generar("sub rbx, " + to_string(varInfo->offset));
            generar("add rbx, rax");
            if (wasFloat) {
                generar("movss xmm0, [rsp]");
                generar("add rsp, 8");
                generar("movss [rbx], xmm0");
                lastExprWasFloat = true;
            } else {
                generar("pop rax");
                if (varInfo->type == DataType::FLOAT) {
                    generar("cvtsi2ss xmm0, rax");
                    generar("movss [rbx], xmm0");
                    lastExprWasFloat = true;
                } else if (varInfo->type == DataType::LONG) {
                    generar("mov [rbx], rax");
                    lastExprWasFloat = false;
                } else {
                    generar("mov [rbx], eax");
                    lastExprWasFloat = false;
                }
            }
        } else if (node->indices.size() == 2) {
            node->indices[0]->accept(this);
            generar("imul rax, " + to_string(varInfo->dimensions[1]));
            generar("push rax");
            node->indices[1]->accept(this);
            generar("pop rbx");
            generar("add rax, rbx");
            int typeSize = 4;
            if (varInfo->type == DataType::LONG) typeSize = 8;
            generar("imul rax, " + to_string(typeSize));
            generar("mov rbx, rbp");
            generar("sub rbx, " + to_string(varInfo->offset));
            generar("add rbx, rax");
            if (wasFloat) {
                generar("movss xmm0, [rsp]");
                generar("add rsp, 8");
                generar("movss [rbx], xmm0");
                lastExprWasFloat = true;
            } else {
                generar("pop rax");
                if (varInfo->type == DataType::FLOAT) {
                    generar("cvtsi2ss xmm0, rax");
                    generar("movss [rbx], xmm0");
                    lastExprWasFloat = true;
                } else if (varInfo->type == DataType::LONG) {
                    generar("mov [rbx], rax");
                    lastExprWasFloat = false;
                } else {
                    generar("mov [rbx], eax");
                    lastExprWasFloat = false;
                }
            }
        }
        if (varInfo->type == DataType::FLOAT) {
            generar("movss xmm0, [rbx]");
            lastExprWasFloat = true;
        } else if (varInfo->type == DataType::LONG) {
            generar("mov rax, [rbx]");
            lastExprWasFloat = false;
        } else {
            generar("mov eax, [rbx]");
            generar("movsx rax, eax");
            lastExprWasFloat = false;
        }
    } else {
        node->value->accept(this);
        if (localVars.find(node->varName) != localVars.end()) {
            VarInfo& var = localVars[node->varName];
            if (var.type == DataType::FLOAT) {
                generar("movss [rbp - " + to_string(var.offset) + "], xmm0");
                lastExprWasFloat = true;
            } else if (var.type == DataType::LONG) {
                generar("mov [rbp - " + to_string(var.offset) + "], rax");
                lastExprWasFloat = false;
            } else {
                generar("mov [rbp - " + to_string(var.offset) + "], eax");
                lastExprWasFloat = false;
            }
        }
    }
}



void CodeGen::visitVarDecl(VarDecl* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->line);
    if (currentFunction.empty()) {
    } else {
        if (optimizedVars.find(node->name) != optimizedVars.end()) {
            VarInfo varInfo;
            varInfo.type = node->type;
            varInfo.offset = 0;
            varInfo.isArray = node->isArray;
            varInfo.dimensions = node->dimensions;
            localVars[node->name] = varInfo;
            currentSourceLine = savedLine;
            return;
        }
        int size = 4;

        if (node->type == DataType::LONG) {
            size = 8;
        }

        if (node->isArray) {
            int totalSize = size;
            for (int dim : node->dimensions) {
                totalSize *= dim;
            }
            stackOffset += totalSize;
        } else {
            stackOffset += size;
        }

        VarInfo varInfo;
        varInfo.type = node->type;
        varInfo.offset = stackOffset;
        varInfo.isArray = node->isArray;
        varInfo.dimensions = node->dimensions;

        localVars[node->name] = varInfo;
        if (debugGen) {
            string typeStr = "int";
            if (node->type == DataType::FLOAT) typeStr = "float";
            else if (node->type == DataType::LONG) typeStr = "long";
            debugGen->logStackVariable(node->name, stackOffset, typeStr,
                                      node->isArray, node->line);
        }

        if (node->initializer) {
            int declLine = currentSourceLine;
            node->initializer->accept(this);
            currentSourceLine = declLine;

            if (node->type == DataType::FLOAT) {
                generar("movss [rbp - " + to_string(stackOffset) + "], xmm0");
            } else if (node->type == DataType::LONG) {
                generar("mov [rbp - " + to_string(stackOffset) + "], rax");
            } else {
                generar("mov [rbp - " + to_string(stackOffset) + "], eax");
            }
        }
    }
    currentSourceLine = savedLine;
}

void CodeGen::visitAssignStmt(AssignStmt* node) {
    int savedLine = currentSourceLine;
    setSourceLine(node->line);
    int assignLine = currentSourceLine;
    if (node->isArrayAssign) {

        node->value->accept(this);
        currentSourceLine = assignLine;
        generar("push rax");

        VarInfo* varInfo = nullptr;
        if (localVars.find(node->varName) != localVars.end()) {
            varInfo = &localVars[node->varName];
        }

        if (!varInfo) {
            currentSourceLine = savedLine;
            return;
        }

        if (node->indices.size() == 1) {
            node->indices[0]->accept(this);
            currentSourceLine = assignLine;

            int typeSize = 4;
            if (varInfo->type == DataType::LONG) typeSize = 8;

            generar("imul rax, " + to_string(typeSize));
            generar("mov rbx, rbp");
            generar("sub rbx, " + to_string(varInfo->offset));
            generar("add rbx, rax");

            generar("pop rax");

            if (varInfo->type == DataType::FLOAT) {
                generar("movss [rbx], xmm0");
            } else if (varInfo->type == DataType::LONG) {
                generar("movsx rax, eax");
                generar("mov [rbx], rax");
            } else {
                generar("mov [rbx], eax");
            }
        } else if (node->indices.size() == 2) {
            node->indices[0]->accept(this);
            currentSourceLine = assignLine;
            generar("imul rax, " + to_string(varInfo->dimensions[1]));
            generar("push rax");

            node->indices[1]->accept(this);
            currentSourceLine = assignLine;
            generar("pop rbx");
            generar("add rax, rbx");

            int typeSize = 4;
            if (varInfo->type == DataType::LONG) typeSize = 8;

            generar("imul rax, " + to_string(typeSize));
            generar("mov rbx, rbp");
            generar("sub rbx, " + to_string(varInfo->offset));
            generar("add rbx, rax");

            generar("pop rax");

            if (varInfo->type == DataType::FLOAT) {
                generar("movss [rbx], xmm0");
            } else if (varInfo->type == DataType::LONG) {
                generar("movsx rax, eax");
                generar("mov [rbx], rax");
            } else {
                generar("mov [rbx], eax");
            }
        }
    } else {
        node->value->accept(this);
        currentSourceLine = assignLine;

        if (localVars.find(node->varName) != localVars.end()) {
            VarInfo& var = localVars[node->varName];

            if (var.type == DataType::FLOAT) {
                generar("movss [rbp - " + to_string(var.offset) + "], xmm0");
            } else if (var.type == DataType::LONG) {
                generar("movsx rax, eax");
                generar("mov [rbp - " + to_string(var.offset) + "], rax");
            } else {
                generar("mov [rbp - " + to_string(var.offset) + "], eax");
            }
        }
    }
    currentSourceLine = savedLine;
}

void CodeGen::visitBlock(Block* node) {
    for (auto& stmt : node->statements) {
        stmt->accept(this);
    }
}

void CodeGen::visitIfStmt(IfStmt* node) {
    setSourceLine(node->line);
    string labelElse = newLabel("else_");
    string labelEnd = newLabel("endif_");

    node->condition->accept(this);
    generar("test rax, rax");

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
    generar("test rax, rax");
    generar("jz " + labelEnd);

    node->body->accept(this);

    generar("jmp " + labelStart);
    generarLabel(labelEnd);
}

void CodeGen::visitForStmt(ForStmt* node) {
    setSourceLine(node->line);
    string labelStart = newLabel("for_start_");
    string labelEnd = newLabel("for_end_");

    if (node->initializer) {
        node->initializer->accept(this);
    }

    generarLabel(labelStart);

    if (node->condition) {
        node->condition->accept(this);
        generar("test rax, rax");
        generar("jz " + labelEnd);
    }


    node->body->accept(this);

    if (node->increment) {
        node->increment->accept(this);
    }

    generar("jmp " + labelStart);
    generarLabel(labelEnd);
}

void CodeGen::visitReturnStmt(ReturnStmt* node) {
    setSourceLine(node->line);
    if (node->value) {
        node->value->accept(this);
    }

    generarEpilogoFuncion();
}

void CodeGen::visitExprStmt(ExprStmt* node) {
    setSourceLine(node->line);
    node->expression->accept(this);
}


void CodeGen::detectOptimizedVars(FunctionDecl* node) {
    optimizedVars.clear();
    set<string> declaredVars;
    set<string> usedVars;
    function<void(Stmt*)> analyzeStmt = [&](Stmt* stmt) {
        if (!stmt) return;
        if (VarDecl* varDecl = dynamic_cast<VarDecl*>(stmt)) {
            declaredVars.insert(varDecl->name);
        }
        if (ReturnStmt* ret = dynamic_cast<ReturnStmt*>(stmt)) {
            if (ret->value) {
                IntLiteral* lit = dynamic_cast<IntLiteral*>(ret->value.get());
                if (lit) {
                } else {
                    Variable* var = dynamic_cast<Variable*>(ret->value.get());
                    if (var) {
                        usedVars.insert(var->name);
                    }
                }
            }
        }
        if (AssignStmt* assign = dynamic_cast<AssignStmt*>(stmt)) {
            usedVars.insert(assign->varName);
        }
        if (Block* block = dynamic_cast<Block*>(stmt)) {
            for (auto& s : block->statements) {
                analyzeStmt(s.get());
            }
        }
        if (IfStmt* ifStmt = dynamic_cast<IfStmt*>(stmt)) {
            analyzeStmt(ifStmt->thenBranch.get());
            if (ifStmt->elseBranch) {
                analyzeStmt(ifStmt->elseBranch.get());
            }
        }
        if (WhileStmt* whileStmt = dynamic_cast<WhileStmt*>(stmt)) {
            analyzeStmt(whileStmt->body.get());
        }
        if (ForStmt* forStmt = dynamic_cast<ForStmt*>(stmt)) {
            if (forStmt->initializer) {
                analyzeStmt(forStmt->initializer.get());
            }
            analyzeStmt(forStmt->body.get());
        }
    };
    analyzeStmt(node->body.get());
    for (const string& var : declaredVars) {
        if (usedVars.find(var) == usedVars.end()) {
            optimizedVars.insert(var);
        }
    }
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
    stackOffset = 0;
    localVars.clear();
    output.str("");
    debugGen = nullptr;
    for (size_t i = 0; i < node->parameters.size() && i < 6; i++) {
        auto& param = node->parameters[i];
        int size = 4;
        if (param.first == DataType::LONG) size = 8;
        stackOffset += size;
        VarInfo varInfo;
        varInfo.type = param.first;
        varInfo.offset = stackOffset;
        varInfo.isArray = false;
        localVars[param.second] = varInfo;
    }
    node->body->accept(this);
    int totalStackSize = stackOffset;
    stackOffset = savedStackOffset;
    localVars = savedLocalVars;
    optimizedVars = savedOptimizedVars;
    output.str("");
    output << savedOutput.str();
    currentSourceLine = savedSourceLine;
    debugGen = savedDebugGen;
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
    for (auto& param : node->parameters) {
        funcInfo.paramTypes.push_back(param.first);
    }
    functions[node->name] = funcInfo;

    int totalStackSize = calculateStackSize(node);
    int paramStackSize = 0;
    for (size_t i = 0; i < node->parameters.size() && i < 6; i++) {
        auto& param = node->parameters[i];
        int size = 4;
        if (param.first == DataType::LONG) size = 8;
        paramStackSize += size;
    }
    int localVarStackSize = totalStackSize - paramStackSize;
    if (localVarStackSize <= 0) {
        localVarStackSize = 0;
    } else {
        if (localVarStackSize % 16 != 0) {
            localVarStackSize = ((localVarStackSize / 16) + 1) * 16;
        }
    }

    generarLabel(node->name);

    currentSourceLine = funcLine;
    generar("push rbp");
    generar("mov rbp, rsp");

    if (localVarStackSize > 0) {
        generar("sub rsp, " + to_string(localVarStackSize));
    }

    vector<string> paramRegs = {"rdi", "rsi", "rdx", "rcx", "r8", "r9"};
    for (size_t i = 0; i < node->parameters.size() && i < 6; i++) {
        auto& param = node->parameters[i];

        int size = 4;
        if (param.first == DataType::LONG) size = 8;

        stackOffset += size;

        VarInfo varInfo;
        varInfo.type = param.first;
        varInfo.offset = stackOffset;
        varInfo.isArray = false;
        localVars[param.second] = varInfo;
        if (debugGen) {
            string typeStr = "int";
            if (param.first == DataType::FLOAT) typeStr = "float";
            else if (param.first == DataType::LONG) typeStr = "long";
            debugGen->logStackVariable(param.second, stackOffset, typeStr,
                                      false, node->line);
        }
        currentSourceLine = funcLine;
        if (param.first == DataType::LONG) {
            generar("mov [rbp - " + to_string(varInfo.offset) + "], " + paramRegs[i]);
        } else {
            string reg32;
            if (paramRegs[i] == "rdi") reg32 = "edi";
            else if (paramRegs[i] == "rsi") reg32 = "esi";
            else if (paramRegs[i] == "rdx") reg32 = "edx";
            else if (paramRegs[i] == "rcx") reg32 = "ecx";
            else if (paramRegs[i] == "r8") reg32 = "r8d";
            else if (paramRegs[i] == "r9") reg32 = "r9d";

            generar("mov [rbp - " + to_string(varInfo.offset) + "], " + reg32);
        }
    }

    node->body->accept(this);

    if (node->returnType == DataType::VOID) {
        currentSourceLine = funcLine;
        generarEpilogoFuncion();
    }

    output << "\n";
    currentFunction = "";
    currentSourceLine = savedLine;
}

