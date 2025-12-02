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
    // Por simplicidad, no gestionamos pool de registros
}

void CodeGen::generarConversionTipo(DataType from, DataType to, string reg) {
    if (from == to) return;

    // INT -> FLOAT
    if (from == DataType::INT && to == DataType::FLOAT) {
        generar("cvtsi2ss xmm0, eax");
    }
    // FLOAT -> INT
    else if (from == DataType::FLOAT && to == DataType::INT) {
        generar("cvttss2si eax, xmm0");
    }
    // INT -> LONG
    else if (from == DataType::INT && to == DataType::LONG) {
        generar("movsx rax, eax");
    }
    // LONG -> INT
    else if (from == DataType::LONG && to == DataType::INT) {
        // Ya está en eax (parte baja de rax)
    }
    // UNSIGNED_INT -> INT (no hacer nada)
    else if (from == DataType::UNSIGNED_INT && to == DataType::INT) {
        // No hacer nada
    }
}

void CodeGen::generarPrologoFuncion(string funcName, int stackSize) {
    // Este método ya no se usa directamente, se emite en visitFunctionDecl
    // Mantener por compatibilidad pero no debería llamarse
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
    // Header del archivo ensamblador
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

    // Generar código para cada declaración
    for (auto& stmt : program->statements) {
        stmt->accept(this);
    }
}

// ========== EXPRESIONES ==========

void CodeGen::visitIntLiteral(IntLiteral* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    generar("mov eax, " + to_string(node->value));
    lastExprWasFloat = false;
}

void CodeGen::visitFloatLiteral(FloatLiteral* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    // Para floats, necesitamos declarar constantes en .data
    string label = newLabel("float_const_");

    // Agregar a sección .data (hacemos trampa: lo emitimos al inicio)
    stringstream temp;
    temp << output.str();

    // Insertar después de "section .data"
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
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    // Limpiar RAX completamente antes de cargar el valor
    // Esto asegura que los 64 bits estén limpios
    generar("xor rax, rax");
    generar("mov eax, " + to_string(node->value));
    lastExprWasFloat = false;
}
void CodeGen::visitStringLiteral(StringLiteral* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    // Para strings, creamos una constante en .data
    string label = newLabel("str_const_");

    // Insertar en sección .data
    string currentOutput = output.str();
    size_t dataPos = currentOutput.find("section .data\n");
    if (dataPos != string::npos) {
        size_t insertPos = currentOutput.find("\n", dataPos + 14) + 1;

        // Construir el string en formato NASM
        string escaped = node->value;
        string nasmStr = "";
        bool hasNewline = false;

        // Procesar caracteres especiales
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
                    i++;  // Saltar el '"'
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

        // Construir la declaración NASM
        string dbLine = "    " + label + ": db \"" + nasmStr + "\"";
        if (hasNewline) {
            dbLine += ", 10";  // Agregar newline como byte separado
        }
        dbLine += ", 0\n";

        currentOutput.insert(insertPos, dbLine);
        output.str("");
        output << currentOutput;
    }

    // Cargar dirección del string en rax
    generar("lea rax, [" + label + "]");
    lastExprWasFloat = false;
}

void CodeGen::visitVariable(Variable* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    // Buscar variable en local o global
    if (localVars.find(node->name) != localVars.end()) {
        VarInfo& var = localVars[node->name];

        if (var.type == DataType::FLOAT) {
            generar("movss xmm0, [rbp - " + to_string(var.offset) + "]");
            lastExprWasFloat = true;
        } else if (var.type == DataType::LONG) {
            generar("mov rax, [rbp - " + to_string(var.offset) + "]");
            lastExprWasFloat = false;
        } else {
            // Cargar y extender directamente desde memoria (más eficiente)
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
    // Guardar línea original
    int savedLine = currentSourceLine;
    // Usar la línea del token del operador
    setSourceLine(node->op.line);
    int opLine = currentSourceLine;  // Guardar línea del operador
    
    // Evaluar operando derecho primero
    node->right->accept(this);
    bool rightWasFloat = lastExprWasFloat;

    // Guardar resultado en stack - usar línea del operador
    currentSourceLine = opLine;
    if (rightWasFloat) {
        generar("sub rsp, 8");
        generar("movss [rsp], xmm0");
    } else {
        generar("push rax");
    }

    // Evaluar operando izquierdo
    node->left->accept(this);
    bool leftWasFloat = lastExprWasFloat;

    // Si alguno es float, la operación será float
    bool isFloatOp = leftWasFloat || rightWasFloat;

    // Recuperar operando derecho - usar línea del operador
    currentSourceLine = opLine;
    if (rightWasFloat) {
        generar("movss xmm1, [rsp]");
        generar("add rsp, 8");
    } else {
        generar("pop rbx");
        // Si left es float pero right no, convertir right a float
        if (isFloatOp && !rightWasFloat) {
            generar("cvtsi2ss xmm1, ebx");
        }
    }

    // Si right es float pero left no, convertir left a float
    if (isFloatOp && !leftWasFloat) {
        generar("cvtsi2ss xmm0, eax");
    }

    // Realizar operación - usar línea del operador
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
                generar("xor rdx, rdx");  // Clear RDX para división
                generar("idiv rbx");
                lastExprWasFloat = false;
            }
            break;

        // Operadores relacionales
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
    
    // Restaurar línea original
    currentSourceLine = savedLine;
}

void CodeGen::visitUnaryOp(UnaryOp* node) {
    // Usar la línea del token del operador
    setSourceLine(node->op.line);
    node->operand->accept(this);

    if (node->op.type == TokenType::MINUS) {
        if (lastExprWasFloat) {
            // Negar float: xor con bit de signo
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
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    node->expr->accept(this);

    // Obtener tipo origen
    DataType fromType = node->expr->inferredType;
    DataType toType = node->targetType;

    // Realizar la conversión y actualizar el flag
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
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    string labelFalse = newLabel("ternary_false_");
    string labelEnd = newLabel("ternary_end_");

    // Evaluar condición
    node->condition->accept(this);
    generar("test rax, rax");
    generar("jz " + labelFalse);

    // Rama verdadera
    node->exprTrue->accept(this);
    generar("jmp " + labelEnd);

    // Rama falsa
    generarLabel(labelFalse);
    node->exprFalse->accept(this);

    generarLabel(labelEnd);
}

void CodeGen::visitCallExpr(CallExpr* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    // Caso especial: printf
    if (node->functionName == "printf") {
        if (node->arguments.size() > 0) {
            // El primer argumento es el formato (string)
            // Verificar si es StringLiteral
            StringLiteral* fmtStr = dynamic_cast<StringLiteral*>(node->arguments[0].get());

            if (fmtStr) {
                // Es un string literal - usar como formato directamente
                fmtStr->accept(this);  // Esto carga la dirección del string en rax
                generar("mov rdi, rax");  // Primer argumento: formato

                // Si hay más argumentos, pasarlos
                if (node->arguments.size() > 1) {
                    // CRÍTICO: Guardar rdi antes de evaluar argumentos que puedan ser llamadas a función
                    generar("push rdi");  // Guardar formato en stack

                    node->arguments[1]->accept(this);

                    // Determinar formato basado en tipo del segundo argumento
                    if (lastExprWasFloat) {
                        generar("cvtss2sd xmm0, xmm0");
                        generar("pop rdi");  // Recuperar formato
                        generar("mov rax, 1");  // 1 registro XMM usado
                    } else {
                        // El valor ya está en rax (extendido si era int)
                        // Para printf en x86-64, pasamos el valor en rsi
                        generar("mov rsi, rax");  // Mover valor completo de rax a rsi
                        generar("pop rdi");  // Recuperar formato
                        generar("xor rax, rax");  // 0 registros XMM usados (printf varargs)
                    }
                } else {
                    generar("xor rax, rax");  // Sin argumentos adicionales
                }
            } else {
                // No es string literal - asumir que es un valor numérico
                node->arguments[0]->accept(this);

                // Determinar formato basado en tipo
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

            // Stack ya está alineado por visitFunctionDecl, solo llamar
            generar("call printf");

        }
    } else {
        // Llamada a función normal

        // Pasar argumentos (convención x86-64: rdi, rsi, rdx, rcx, r8, r9)
        vector<string> argRegs = {"rdi", "rsi", "rdx", "rcx", "r8", "r9"};

        for (size_t i = 0; i < node->arguments.size() && i < 6; i++) {
            node->arguments[i]->accept(this);
            generar("mov " + argRegs[i] + ", rax");
        }

        generar("call " + node->functionName);
    }
}

void CodeGen::visitArrayAccess(ArrayAccess* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    // Buscar info del array
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

    // Calcular offset para arrays multidimensionales
    // arr[i][j] en arr[3][4] = arr[i * 4 + j]

    if (node->indices.size() == 1) {
        // Array 1D simple: arr[i]
        node->indices[0]->accept(this);

        // Multiplicar por tamaño del tipo
        int typeSize = 4; // int, float = 4 bytes
        if (varInfo->type == DataType::LONG) typeSize = 8;

        generar("imul rax, " + to_string(typeSize));
        generar("mov rbx, rbp");
        generar("sub rbx, " + to_string(varInfo->offset));
        generar("add rbx, rax");

        // Cargar valor
        if (varInfo->type == DataType::FLOAT) {
            generar("movss xmm0, [rbx]");
            lastExprWasFloat = true;
        } else {
            generar("mov eax, [rbx]");
            generar("movsx rax, eax");
            lastExprWasFloat = false;
        }
    } else if (node->indices.size() == 2) {
        // Array 2D: arr[i][j]
        // offset = (i * cols + j) * typeSize

        node->indices[0]->accept(this);  // i
        generar("imul rax, " + to_string(varInfo->dimensions[1]));
        generar("push rax");

        node->indices[1]->accept(this);  // j
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
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    if (node->isArrayAssign) {
        // Asignación a array: arr[i] = value
        // Similar a AssignStmt pero el resultado debe quedar en rax/xmm0
        
        // Evaluar valor primero
        node->value->accept(this);
        bool wasFloat = lastExprWasFloat;
        
        // Guardar valor temporalmente
        if (wasFloat) {
            generar("sub rsp, 8");
            generar("movss [rsp], xmm0");
        } else {
            generar("push rax");
        }
        
        // Calcular dirección del array (similar a visitArrayAccess)
        VarInfo* varInfo = nullptr;
        if (localVars.find(node->varName) != localVars.end()) {
            varInfo = &localVars[node->varName];
        }
        
        if (!varInfo) {
            generar("add rsp, 8");  // Limpiar stack
            return;
        }
        
        if (node->indices.size() == 1) {
            // Array 1D
            node->indices[0]->accept(this);
            
            int typeSize = 4;
            if (varInfo->type == DataType::LONG) typeSize = 8;
            
            generar("imul rax, " + to_string(typeSize));
            generar("mov rbx, rbp");
            generar("sub rbx, " + to_string(varInfo->offset));
            generar("add rbx, rax");
            
            // Recuperar y almacenar valor
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
            // Array 2D
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
            
            // Recuperar y almacenar valor
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
        
        // Cargar el valor de vuelta para que quede en rax/xmm0
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
        // Asignación simple: x = value
        node->value->accept(this); // Value is in rax/xmm0
        
        if (localVars.find(node->varName) != localVars.end()) {
            VarInfo& var = localVars[node->varName];
            
            if (var.type == DataType::FLOAT) {
                generar("movss [rbp - " + to_string(var.offset) + "], xmm0");
                // El valor ya está en xmm0
                lastExprWasFloat = true;
            } else if (var.type == DataType::LONG) {
                generar("mov [rbp - " + to_string(var.offset) + "], rax");
                // El valor ya está en rax
                lastExprWasFloat = false;
            } else {
                generar("mov [rbp - " + to_string(var.offset) + "], eax");
                // El valor ya está en rax (eax)
                lastExprWasFloat = false;
            }
        }
        // The result of an assignment expression is the value assigned
        // So, rax/xmm0 already holds the correct value.
    }
}

// ========== STATEMENTS ==========

void CodeGen::visitVarDecl(VarDecl* node) {
    // Guardar la línea de la declaración
    int savedLine = currentSourceLine;
    setSourceLine(node->line);
    
    if (currentFunction.empty()) {
        // Variable global
        // TODO: Implementar variables globales en .bss
    } else {
        // DEAD CODE ELIMINATION: Si la variable fue optimizada y no necesita stack space, saltarla
        if (optimizedVars.find(node->name) != optimizedVars.end()) {
            // Variable optimizada, no necesita espacio en el stack
            // Pero aún así registrarla en localVars (con offset 0) por si se necesita para debug
            VarInfo varInfo;
            varInfo.type = node->type;
            varInfo.offset = 0;  // No tiene offset real porque no está en el stack
            varInfo.isArray = node->isArray;
            varInfo.dimensions = node->dimensions;
            localVars[node->name] = varInfo;
            currentSourceLine = savedLine;  // Restaurar línea
            return;  // No reservar espacio en el stack
        }
        
        // Variable local
        int size = 4; // Por defecto int, float

        if (node->type == DataType::LONG) {
            size = 8;
        }

        if (node->isArray) {
            // Calcular tamaño total del array
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
        
        // Registrar en debug si está habilitado
        if (debugGen) {
            string typeStr = "int";
            if (node->type == DataType::FLOAT) typeStr = "float";
            else if (node->type == DataType::LONG) typeStr = "long";
            
            debugGen->logStackVariable(node->name, stackOffset, typeStr, 
                                      node->isArray, node->line);
        }

        // Si hay inicializador
        if (node->initializer) {
            // Guardar la línea de la declaración antes de evaluar el inicializador
            int declLine = currentSourceLine;
            node->initializer->accept(this);
            // Restaurar la línea de la declaración para las instrucciones de almacenamiento
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
    
    // Restaurar línea original
    currentSourceLine = savedLine;
}

void CodeGen::visitAssignStmt(AssignStmt* node) {
    // Guardar línea original
    int savedLine = currentSourceLine;
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    int assignLine = currentSourceLine;  // Guardar línea de la asignación
    
    if (node->isArrayAssign) {
        // Asignación a array: arr[i] = value

        // Evaluar valor primero
        node->value->accept(this);
        // Restaurar línea de asignación para push
        currentSourceLine = assignLine;
        generar("push rax");  // Guardar valor

        // Calcular dirección del array
        VarInfo* varInfo = nullptr;
        if (localVars.find(node->varName) != localVars.end()) {
            varInfo = &localVars[node->varName];
        }

        if (!varInfo) {
            currentSourceLine = savedLine;
            return;
        }

        if (node->indices.size() == 1) {
            // Array 1D
            node->indices[0]->accept(this);
            // Restaurar línea de asignación
            currentSourceLine = assignLine;

            int typeSize = 4;
            if (varInfo->type == DataType::LONG) typeSize = 8;

            generar("imul rax, " + to_string(typeSize));
            generar("mov rbx, rbp");
            generar("sub rbx, " + to_string(varInfo->offset));
            generar("add rbx, rax");

            generar("pop rax");  // Recuperar valor

            if (varInfo->type == DataType::FLOAT) {
                generar("movss [rbx], xmm0");
            } else if (varInfo->type == DataType::LONG) {
                // Para long, asegurarse de extender correctamente
                generar("movsx rax, eax");
                generar("mov [rbx], rax");
            } else {
                generar("mov [rbx], eax");
            }
        } else if (node->indices.size() == 2) {
            // Array 2D
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

            generar("pop rax");  // Recuperar valor

            if (varInfo->type == DataType::FLOAT) {
                generar("movss [rbx], xmm0");
            } else if (varInfo->type == DataType::LONG) {
                // Para long, asegurarse de extender correctamente
                generar("movsx rax, eax");
                generar("mov [rbx], rax");
            } else {
                generar("mov [rbx], eax");
            }
        }
    } else {
        // Asignación simple: x = value
        node->value->accept(this);
        // Restaurar línea de asignación para las instrucciones de almacenamiento
        currentSourceLine = assignLine;

        if (localVars.find(node->varName) != localVars.end()) {
            VarInfo& var = localVars[node->varName];

            if (var.type == DataType::FLOAT) {
                generar("movss [rbp - " + to_string(var.offset) + "], xmm0");
            } else if (var.type == DataType::LONG) {
                // Si el valor viene de un int, extenderlo a long
                generar("movsx rax, eax");
                generar("mov [rbp - " + to_string(var.offset) + "], rax");
            } else {
                generar("mov [rbp - " + to_string(var.offset) + "], eax");
            }
        }
    }
    
    // Restaurar línea original
    currentSourceLine = savedLine;
}

void CodeGen::visitBlock(Block* node) {
    for (auto& stmt : node->statements) {
        stmt->accept(this);
    }
}

void CodeGen::visitIfStmt(IfStmt* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    string labelElse = newLabel("else_");
    string labelEnd = newLabel("endif_");

    // Evaluar condición
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
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    string labelStart = newLabel("while_start_");
    string labelEnd = newLabel("while_end_");

    generarLabel(labelStart);

    // Evaluar condición
    node->condition->accept(this);
    generar("test rax, rax");
    generar("jz " + labelEnd);

    // Cuerpo del while
    node->body->accept(this);

    generar("jmp " + labelStart);
    generarLabel(labelEnd);
}

void CodeGen::visitForStmt(ForStmt* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    string labelStart = newLabel("for_start_");
    string labelEnd = newLabel("for_end_");

    // Inicializador
    if (node->initializer) {
        node->initializer->accept(this);
    }

    generarLabel(labelStart);

    // Condición
    if (node->condition) {
        node->condition->accept(this);
        generar("test rax, rax");
        generar("jz " + labelEnd);
    }


    // Cuerpo
    node->body->accept(this);

    // Incremento
    if (node->increment) {
        node->increment->accept(this);
    }

    generar("jmp " + labelStart);
    generarLabel(labelEnd);
}

void CodeGen::visitReturnStmt(ReturnStmt* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    if (node->value) {
        node->value->accept(this);
    }

    generarEpilogoFuncion();
}

void CodeGen::visitExprStmt(ExprStmt* node) {
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    
    node->expression->accept(this);
}

// Helper para detectar variables optimizadas que no necesitan stack space
void CodeGen::detectOptimizedVars(FunctionDecl* node) {
    optimizedVars.clear();
    
    // Analizar el cuerpo para encontrar variables que fueron optimizadas
    // Estrategia: Si un return statement es un literal (fue optimizado de variable a constante),
    // entonces las variables que solo se usaban en ese return no necesitan stack
    
    set<string> declaredVars;  // Variables declaradas
    set<string> usedVars;      // Variables realmente usadas (no optimizadas)
    
    function<void(Stmt*)> analyzeStmt = [&](Stmt* stmt) {
        if (!stmt) return;
        
        // Si es una declaración de variable
        if (VarDecl* varDecl = dynamic_cast<VarDecl*>(stmt)) {
            declaredVars.insert(varDecl->name);
        }
        
        // Si es un return
        if (ReturnStmt* ret = dynamic_cast<ReturnStmt*>(stmt)) {
            if (ret->value) {
                // Si el return es un literal, significa que fue optimizado
                // (originalmente era return var, ahora es return 6)
                IntLiteral* lit = dynamic_cast<IntLiteral*>(ret->value.get());
                if (lit) {
                    // Return optimizado a constante - las variables que solo se usaban aquí
                    // fueron optimizadas y no necesitan stack
                    // (las detectaremos porque no aparecen en usedVars)
                } else {
                    // Return usa una variable - marcarla como usada
                    Variable* var = dynamic_cast<Variable*>(ret->value.get());
                    if (var) {
                        usedVars.insert(var->name);
                    }
                }
            }
        }
        
        // Si es una asignación, la variable destino se usa
        if (AssignStmt* assign = dynamic_cast<AssignStmt*>(stmt)) {
            usedVars.insert(assign->varName);
        }
        
        // Recursivamente analizar bloques
        if (Block* block = dynamic_cast<Block*>(stmt)) {
            for (auto& s : block->statements) {
                analyzeStmt(s.get());
            }
        }
        
        // Analizar otros tipos de statements recursivamente
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
    
    // Variables declaradas pero no usadas = optimizadas/eliminadas
    // Estas no necesitan espacio en el stack
    for (const string& var : declaredVars) {
        if (usedVars.find(var) == usedVars.end()) {
            optimizedVars.insert(var);
        }
    }
}

// Helper para calcular el tamaño del stack sin generar código
int CodeGen::calculateStackSize(FunctionDecl* node) {
    int savedStackOffset = stackOffset;
    map<string, VarInfo> savedLocalVars = localVars;
    set<string> savedOptimizedVars = optimizedVars;
    stringstream savedOutput;
    savedOutput << output.str();
    int savedSourceLine = currentSourceLine;
    DebugGen* savedDebugGen = debugGen;  // Guardar debugGen
    
    // PRIMERO: Detectar variables optimizadas
    detectOptimizedVars(node);
    
    // Resetear para cálculo
    stackOffset = 0;
    localVars.clear();
    output.str("");  // Limpiar output temporalmente
    debugGen = nullptr;  // Deshabilitar debug durante el cálculo (no queremos registrar instrucciones temporales)
    
    // Calcular espacio para parámetros
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
    
    // Visitar el cuerpo para calcular variables locales
    // visitVarDecl actualizará stackOffset sin generar código útil (solo en output temporal)
    node->body->accept(this);
    
    int totalStackSize = stackOffset;
    
    // Restaurar estado
    stackOffset = savedStackOffset;
    localVars = savedLocalVars;
    optimizedVars = savedOptimizedVars;
    output.str("");
    output << savedOutput.str();
    currentSourceLine = savedSourceLine;
    debugGen = savedDebugGen;  // Restaurar debugGen
    
    return totalStackSize;
}

void CodeGen::visitFunctionDecl(FunctionDecl* node) {
    // Guardar línea original
    int savedLine = currentSourceLine;
    // Usar la línea del nodo AST
    setSourceLine(node->line);
    int funcLine = currentSourceLine;  // Guardar línea de la función
    
    currentFunction = node->name;
    localVars.clear();
    stackOffset = 0;

    // Registrar función
    FunctionInfo funcInfo;
    funcInfo.returnType = node->returnType;
    for (auto& param : node->parameters) {
        funcInfo.paramTypes.push_back(param.first);
    }
    functions[node->name] = funcInfo;

    // PRIMERO: Calcular el tamaño real del stack necesario
    int totalStackSize = calculateStackSize(node);
    
    // Calcular espacio solo para variables locales (sin parámetros)
    int paramStackSize = 0;
    for (size_t i = 0; i < node->parameters.size() && i < 6; i++) {
        auto& param = node->parameters[i];
        int size = 4;
        if (param.first == DataType::LONG) size = 8;
        paramStackSize += size;
    }
    
    int localVarStackSize = totalStackSize - paramStackSize;
    
    // DEAD CODE ELIMINATION: Solo reservar stack si realmente hay variables locales
    // Si localVarStackSize es 0 o negativo, no hay variables locales
    if (localVarStackSize <= 0) {
        localVarStackSize = 0;
    } else {
        // Alinear a 16 bytes solo si hay variables locales (requisito de ABI x86-64)
        if (localVarStackSize % 16 != 0) {
            localVarStackSize = ((localVarStackSize / 16) + 1) * 16;
        }
    }

    // Emitir label de función (sin línea específica, es metadata)
    generarLabel(node->name);

    // Prólogo - usar línea de la función
    currentSourceLine = funcLine;
    generar("push rbp");
    generar("mov rbp, rsp");

    // DEAD CODE ELIMINATION: Reservar espacio en el stack SOLO si hay variables locales
    // Si no hay variables locales, no necesitamos reservar stack (los parámetros están en registros)
    if (localVarStackSize > 0) {
        generar("sub rsp, " + to_string(localVarStackSize));
    }

    // Guardar parámetros en stack y calcular stackOffset inicial
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
        
        // Registrar parámetro en debug si está habilitado
        if (debugGen) {
            string typeStr = "int";
            if (param.first == DataType::FLOAT) typeStr = "float";
            else if (param.first == DataType::LONG) typeStr = "long";
            
            debugGen->logStackVariable(param.second, stackOffset, typeStr, 
                                      false, node->line);
        }
        
        // Guardar parámetro en stack - usar línea de la función
        currentSourceLine = funcLine;
        if (param.first == DataType::LONG) {
            generar("mov [rbp - " + to_string(varInfo.offset) + "], " + paramRegs[i]);
        } else {
            // Para registros de 32 bits: rdi->edi, rsi->esi, etc.
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

    // Cuerpo de la función (DESPUÉS de reservar stack y guardar parámetros)
    // El cuerpo establecerá sus propias líneas según los statements
    node->body->accept(this);

    // Si no hubo return explícito
    if (node->returnType == DataType::VOID) {
        // Usar línea del final de la función (última línea del bloque)
        currentSourceLine = funcLine;
        generarEpilogoFuncion();
    }

    output << "\n";
    
    // NO limpiar stack frame - necesitamos todas las variables para el debugger
    // El stackFrame se mantiene con todas las variables de todas las funciones
    // para que el emulador pueda mostrar el call stack completo
    // if (debugGen) {
    //     debugGen->clearStackFrame();
    // }
    
    currentFunction = "";
    // Restaurar línea original
    currentSourceLine = savedLine;
}

