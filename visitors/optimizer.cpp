#include "optimizer.h"

#include <iostream>

Optimizer::Optimizer() {
}

void Optimizer::optimize(Program* program) {
    cout << "  Applying optimizations..." << endl;

    for (auto& stmt : program->statements) {
        optimizeStmt(stmt.get());
    }

    cout << "  Optimizations complete!" << endl;
}

void Optimizer::optimizeStmt(Stmt* stmt) {
    if (VarDecl* varDecl = dynamic_cast<VarDecl*>(stmt)) {
        if (varDecl->initializer) {
            varDecl->initializer = optimizeExpr(varDecl->initializer.get());

            int value;
            if (isIntLiteral(varDecl->initializer.get(), value)) {
                constantValues[varDecl->name] = value;
                cout << "    Propagating constant: " << varDecl->name << " = " << value << endl;
            }
        }
    }

    else if (AssignStmt* assign = dynamic_cast<AssignStmt*>(stmt)) {
        assign->value = optimizeExpr(assign->value.get());

        int value;
        if (isIntLiteral(assign->value.get(), value)) {
            constantValues[assign->varName] = value;
            cout << "    Propagating constant: " << assign->varName << " = " << value << endl;
        } else {
            constantValues.erase(assign->varName);
        }
    }

    else if (Block* block = dynamic_cast<Block*>(stmt)) {
        optimizeBlock(block);
    }

    else if (IfStmt* ifStmt = dynamic_cast<IfStmt*>(stmt)) {
        ifStmt->condition = optimizeExpr(ifStmt->condition.get());

        optimizeStmt(ifStmt->thenBranch.get());

        if (ifStmt->elseBranch) {
            optimizeStmt(ifStmt->elseBranch.get());
        }
    }

    else if (WhileStmt* whileStmt = dynamic_cast<WhileStmt*>(stmt)) {
        whileStmt->condition = optimizeExpr(whileStmt->condition.get());

        optimizeStmt(whileStmt->body.get());
    }

    else if (ForStmt* forStmt = dynamic_cast<ForStmt*>(stmt)) {
        if (forStmt->initializer) {
            optimizeStmt(forStmt->initializer.get());
        }

        if (forStmt->condition) {
            forStmt->condition = optimizeExpr(forStmt->condition.get());
        }

        if (forStmt->increment) {
            forStmt->increment = optimizeExpr(forStmt->increment.get());
        }

        optimizeStmt(forStmt->body.get());
    }

    else if (ReturnStmt* returnStmt = dynamic_cast<ReturnStmt*>(stmt)) {
        if (returnStmt->value) {
            returnStmt->value = optimizeExpr(returnStmt->value.get());
        }
    }

    else if (FunctionDecl* funcDecl = dynamic_cast<FunctionDecl*>(stmt)) {
        constantValues.clear();

        optimizeBlock(funcDecl->body.get());
    }

    else if (ExprStmt* exprStmt = dynamic_cast<ExprStmt*>(stmt)) {
        exprStmt->expression = optimizeExpr(exprStmt->expression.get());
    }
}

void Optimizer::optimizeBlock(Block* block) {
    vector<unique_ptr<Stmt>> optimizedStmts;

    for (auto& stmt : block->statements) {
        if (ForStmt* forStmt = dynamic_cast<ForStmt*>(stmt.get())) {
            if (tryEvaluateConstantLoop(forStmt, optimizedStmts)) {
                continue;
            }
            if (tryUnrollLoop(forStmt, optimizedStmts)) {
                continue;
            }
        }

        if (IfStmt* ifStmt = dynamic_cast<IfStmt*>(stmt.get())) {
            ifStmt->condition = optimizeExpr(ifStmt->condition.get());

            int condValue;
            if (isIntLiteral(ifStmt->condition.get(), condValue)) {
                if (condValue == 0) {
                    cout << "    Eliminated dead code: if (0) { ... } block removed" << endl;

                    if (ifStmt->elseBranch) {
                        cout << "    Keeping else branch" << endl;
                        optimizeStmt(ifStmt->elseBranch.get());
                        optimizedStmts.push_back(move(ifStmt->elseBranch));
                    }
                    continue;
                }
                else {
                    cout << "    Eliminated dead code: condition always true, removed else branch" << endl;

                    optimizeStmt(ifStmt->thenBranch.get());
                    optimizedStmts.push_back(move(ifStmt->thenBranch));
                    continue;
                }
            }
        }

        optimizeStmt(stmt.get());
        optimizedStmts.push_back(move(stmt));
    }

    block->statements = move(optimizedStmts);
    
    eliminateDeadStores(block);
}

unique_ptr<Expr> Optimizer::optimizeExpr(Expr* expr) {
    if (IntLiteral* lit = dynamic_cast<IntLiteral*>(expr)) {
        auto cloned = make_unique<IntLiteral>(lit->value);
        cloned->line = lit->line;
        return cloned;
    }

    else if (FloatLiteral* lit = dynamic_cast<FloatLiteral*>(expr)) {
        auto cloned = make_unique<FloatLiteral>(lit->value);
        cloned->line = lit->line;
        return cloned;
    }

    else if (LongLiteral* lit = dynamic_cast<LongLiteral*>(expr)) {
        auto cloned = make_unique<LongLiteral>(lit->value);
        cloned->line = lit->line;
        return cloned;
    }

    else if (StringLiteral* lit = dynamic_cast<StringLiteral*>(expr)) {
        auto cloned = make_unique<StringLiteral>(lit->value);
        cloned->line = lit->line;
        return cloned;
    }

    else if (Variable* var = dynamic_cast<Variable*>(expr)) {
        if (constantValues.find(var->name) != constantValues.end()) {
            int value = constantValues[var->name];
            cout << "    Replacing variable " << var->name << " with " << value << endl;
            auto cloned = make_unique<IntLiteral>(value);
            cloned->line = var->line;
            return cloned;
        }

        auto cloned = make_unique<Variable>(var->name);
        cloned->line = var->line;
        return cloned;
    }

    else if (BinaryOp* binOp = dynamic_cast<BinaryOp*>(expr)) {
        return optimizeBinaryOp(binOp);
    }

    else if (UnaryOp* unOp = dynamic_cast<UnaryOp*>(expr)) {
        auto optimizedOperand = optimizeExpr(unOp->operand.get());

        int value;
        if (isIntLiteral(optimizedOperand.get(), value)) {
            if (unOp->op.type == TokenType::MINUS) {
                auto cloned = make_unique<IntLiteral>(-value);
                cloned->line = unOp->line;
                return cloned;
            }
        }

        auto cloned = make_unique<UnaryOp>(unOp->op, move(optimizedOperand));
        cloned->line = unOp->line;
        return cloned;
    }

    else if (CastExpr* cast = dynamic_cast<CastExpr*>(expr)) {
        auto optimizedExpr = optimizeExpr(cast->expr.get());
        auto cloned = make_unique<CastExpr>(cast->targetType, move(optimizedExpr));
        cloned->line = cast->line;
        return cloned;
    }

    else if (TernaryExpr* ternary = dynamic_cast<TernaryExpr*>(expr)) {
        auto optimizedCond = optimizeExpr(ternary->condition.get());
        auto optimizedTrue = optimizeExpr(ternary->exprTrue.get());
        auto optimizedFalse = optimizeExpr(ternary->exprFalse.get());

        auto cloned = make_unique<TernaryExpr>(
            move(optimizedCond),
            move(optimizedTrue),
            move(optimizedFalse)
        );
        cloned->line = ternary->line;
        return cloned;
    }

    else if (CallExpr* call = dynamic_cast<CallExpr*>(expr)) {
        vector<unique_ptr<Expr>> optimizedArgs;
        for (auto& arg : call->arguments) {
            optimizedArgs.push_back(optimizeExpr(arg.get()));
        }

        auto cloned = make_unique<CallExpr>(call->functionName, move(optimizedArgs));
        cloned->line = call->line;
        return cloned;
    }

    else if (ArrayAccess* arrAccess = dynamic_cast<ArrayAccess*>(expr)) {
        vector<unique_ptr<Expr>> optimizedIndices;
        for (auto& index : arrAccess->indices) {
            optimizedIndices.push_back(optimizeExpr(index.get()));
        }

        auto cloned = make_unique<ArrayAccess>(arrAccess->arrayName, move(optimizedIndices));
        cloned->line = arrAccess->line;
        return cloned;
    }

    else if (AssignExpr* assignExpr = dynamic_cast<AssignExpr*>(expr)) {
        auto optimizedValue = optimizeExpr(assignExpr->value.get());
        
        int value;
        if (isIntLiteral(optimizedValue.get(), value)) {
            constantValues[assignExpr->varName] = value;
        } else {
            constantValues.erase(assignExpr->varName);
        }
        
        unique_ptr<AssignExpr> cloned;
        if (assignExpr->isArrayAssign) {
            vector<unique_ptr<Expr>> optimizedIndices;
            for (auto& index : assignExpr->indices) {
                optimizedIndices.push_back(optimizeExpr(index.get()));
            }
            cloned = make_unique<AssignExpr>(assignExpr->varName, move(optimizedIndices), move(optimizedValue));
        } else {
            cloned = make_unique<AssignExpr>(assignExpr->varName, move(optimizedValue));
        }
        cloned->line = assignExpr->line;
        return cloned;
    }

    return nullptr;
}

unique_ptr<Expr> Optimizer::optimizeBinaryOp(BinaryOp* node) {
    auto left = optimizeExpr(node->left.get());
    auto right = optimizeExpr(node->right.get());

    int leftValue, rightValue;
    bool leftIsLiteral = isIntLiteral(left.get(), leftValue);
    bool rightIsLiteral = isIntLiteral(right.get(), rightValue);

    if (leftIsLiteral && rightIsLiteral) {
        int result = calculate(leftValue, node->op.type, rightValue);

        cout << "    Folded: " << leftValue << " "
             << node->op.lexeme << " " << rightValue
             << " -> " << result << endl;

        auto cloned = make_unique<IntLiteral>(result);
        cloned->line = node->line;
        return cloned;
    }

    if (node->op.type == TokenType::MULTIPLY) {
        if (rightIsLiteral && rightValue == 0) {
            cout << "    Simplified: x * 0 -> 0" << endl;
            auto cloned = make_unique<IntLiteral>(0);
            cloned->line = node->line;
            return cloned;
        }
        if (leftIsLiteral && leftValue == 0) {
            cout << "    Simplified: 0 * x -> 0" << endl;
            auto cloned = make_unique<IntLiteral>(0);
            cloned->line = node->line;
            return cloned;
        }

        if (rightIsLiteral && rightValue == 1) {
            cout << "    Simplified: x * 1 -> x" << endl;
            return left;
        }
        if (leftIsLiteral && leftValue == 1) {
            cout << "    Simplified: 1 * x -> x" << endl;
            return right;
        }

        if (rightIsLiteral && (rightValue & (rightValue - 1)) == 0 && rightValue > 0) {
            int shiftAmount = 0;
            int temp = rightValue;
            while (temp > 1) {
                temp >>= 1;
                shiftAmount++;
            }

            cout << "    Optimized: x * " << rightValue << " -> x << " << shiftAmount << endl;

            Token shiftToken(TokenType::UNKNOWN, "<<", node->op.line, node->op.column);
            auto shiftAmountLit = make_unique<IntLiteral>(shiftAmount);
            shiftAmountLit->line = node->line;
            auto cloned = make_unique<BinaryOp>(
                move(left),
                shiftToken,
                move(shiftAmountLit)
            );
            cloned->line = node->line;
            return cloned;
        }
    }

    if (node->op.type == TokenType::PLUS) {
        if (rightIsLiteral && rightValue == 0) {
            cout << "    Simplified: x + 0 -> x" << endl;
            return left;
        }
        if (leftIsLiteral && leftValue == 0) {
            cout << "    Simplified: 0 + x -> x" << endl;
            return right;
        }
    }

    if (node->op.type == TokenType::MINUS) {
        if (rightIsLiteral && rightValue == 0) {
            cout << "    Simplified: x - 0 -> x" << endl;
            return left;
        }
    }

    if (node->op.type == TokenType::DIVIDE) {
        if (rightIsLiteral && rightValue == 1) {
            cout << "    Simplified: x / 1 -> x" << endl;
            return left;
        }

        if (rightIsLiteral && (rightValue & (rightValue - 1)) == 0 && rightValue > 0) {
            int shiftAmount = 0;
            int temp = rightValue;
            while (temp > 1) {
                temp >>= 1;
                shiftAmount++;
            }

            cout << "    Optimized: x / " << rightValue << " -> x >> " << shiftAmount << endl;

            Token shiftToken(TokenType::UNKNOWN, ">>", node->op.line, node->op.column);
            auto shiftAmountLit = make_unique<IntLiteral>(shiftAmount);
            shiftAmountLit->line = node->line;
            auto cloned = make_unique<BinaryOp>(
                move(left),
                shiftToken,
                move(shiftAmountLit)
            );
            cloned->line = node->line;
            return cloned;
        }
    }

    auto cloned = make_unique<BinaryOp>(move(left), node->op, move(right));
    cloned->line = node->line;
    return cloned;
}

bool Optimizer::isIntLiteral(Expr* expr, int& value) {
    if (IntLiteral* lit = dynamic_cast<IntLiteral*>(expr)) {
        value = lit->value;
        return true;
    }
    return false;
}

int Optimizer::calculate(int left, TokenType op, int right) {
    switch(op) {
        case TokenType::PLUS:
            return left + right;

        case TokenType::MINUS:
            return left - right;

        case TokenType::MULTIPLY:
            return left * right;

        case TokenType::DIVIDE:
            if (right == 0) {
                cerr << "Warning: Division by zero in constant folding" << endl;
                return 0;
            }
            return left / right;

        case TokenType::MODULO:
            if (right == 0) {
                cerr << "Warning: Modulo by zero in constant folding" << endl;
                return 0;
            }
            return left % right;

        default:
            cerr << "Warning: Cannot fold operator" << endl;
            return 0;
    }
}

bool Optimizer::tryUnrollLoop(ForStmt* forStmt, vector<unique_ptr<Stmt>>& output) {
    if (!forStmt->initializer) return false;

    VarDecl* initDecl = dynamic_cast<VarDecl*>(forStmt->initializer.get());
    AssignStmt* initAssign = dynamic_cast<AssignStmt*>(forStmt->initializer.get());

    string loopVar;
    int startValue;

    if (initDecl) {
        if (!initDecl->initializer) return false;
        if (!isIntLiteral(initDecl->initializer.get(), startValue)) return false;
        loopVar = initDecl->name;
    } else if (initAssign) {
        if (!isIntLiteral(initAssign->value.get(), startValue)) return false;
        loopVar = initAssign->varName;
    } else {
        return false;
    }

    if (!forStmt->condition) return false;

    BinaryOp* condition = dynamic_cast<BinaryOp*>(forStmt->condition.get());
    if (!condition || condition->op.type != TokenType::LT) return false;

    Variable* condVar = dynamic_cast<Variable*>(condition->left.get());
    if (!condVar || condVar->name != loopVar) return false;

    int endValue;
    if (!isIntLiteral(condition->right.get(), endValue)) return false;

    if (!forStmt->increment) return false;

    AssignExpr* incAssign = dynamic_cast<AssignExpr*>(forStmt->increment.get());

    if (!incAssign || incAssign->varName != loopVar) return false;

    BinaryOp* incExpr = dynamic_cast<BinaryOp*>(incAssign->value.get());
    if (!incExpr || incExpr->op.type != TokenType::PLUS) return false;

    Variable* incVar = dynamic_cast<Variable*>(incExpr->left.get());
    if (!incVar || incVar->name != loopVar) return false;

    int incValue;
    if (!isIntLiteral(incExpr->right.get(), incValue)) return false;
    if (incValue != 1) return false;

    int iterations = (endValue - startValue) / incValue;

    if (iterations <= 0 || iterations > 10) {
        return false;
    }

    cout << "    Unrolling loop: " << iterations << " iterations" << endl;

    output.push_back(cloneStmt(forStmt->initializer.get()));

    for (int i = startValue; i < endValue; i += incValue) {
        int savedValue = 0;
        bool hadValue = false;

        if (constantValues.find(loopVar) != constantValues.end()) {
            savedValue = constantValues[loopVar];
            hadValue = true;
        }

        constantValues[loopVar] = i;

        auto bodyClone = cloneStmt(forStmt->body.get());
        if (bodyClone) {
            optimizeStmt(bodyClone.get());

            if (Block* bodyBlock = dynamic_cast<Block*>(bodyClone.get())) {
                for (auto& s : bodyBlock->statements) {
                    output.push_back(move(s));
                }
            } else {
                output.push_back(move(bodyClone));
            }
        }

        if (hadValue) {
            constantValues[loopVar] = savedValue;
        } else {
            constantValues.erase(loopVar);
        }
    }

    constantValues.erase(loopVar);

    return true;
}

bool Optimizer::tryEvaluateConstantLoop(ForStmt* forStmt, vector<unique_ptr<Stmt>>& output) {
    if (!forStmt->initializer) return false;

    VarDecl* initDecl = dynamic_cast<VarDecl*>(forStmt->initializer.get());
    if (!initDecl || !initDecl->initializer) return false;

    int startValue;
    if (!isIntLiteral(initDecl->initializer.get(), startValue)) return false;
    string loopVar = initDecl->name;

    if (!forStmt->condition) return false;

    BinaryOp* condition = dynamic_cast<BinaryOp*>(forStmt->condition.get());
    if (!condition) return false;

    // Soporte para < y <=
    if (condition->op.type != TokenType::LT && condition->op.type != TokenType::LE)
        return false;

    Variable* condVar = dynamic_cast<Variable*>(condition->left.get());
    if (!condVar || condVar->name != loopVar) return false;

    int endValue;
    if (!isIntLiteral(condition->right.get(), endValue)) return false;

    // Ajustar para <=
    if (condition->op.type == TokenType::LE) {
        endValue++;
    }

    if (!forStmt->increment) return false;

    int incValue = 1;
    AssignExpr* incAssign = dynamic_cast<AssignExpr*>(forStmt->increment.get());
    if (incAssign && incAssign->varName == loopVar) {
        BinaryOp* incExpr = dynamic_cast<BinaryOp*>(incAssign->value.get());
        if (incExpr && incExpr->op.type == TokenType::PLUS) {
            Variable* incVar = dynamic_cast<Variable*>(incExpr->left.get());
            if (incVar && incVar->name == loopVar) {
                if (!isIntLiteral(incExpr->right.get(), incValue)) return false;
            } else {
                return false;
            }
        } else {
            return false;
        }
    } else {
        return false;
    }

    Block* bodyBlock = dynamic_cast<Block*>(forStmt->body.get());
    if (!bodyBlock || bodyBlock->statements.size() != 1) return false;

    Stmt* bodyStmt = bodyBlock->statements[0].get();
    string accumVar;
    TokenType accumOp;
    bool isAccumulation = false;

    if (AssignStmt* assign = dynamic_cast<AssignStmt*>(bodyStmt)) {
        if (assign->value) {
            BinaryOp* binOp = dynamic_cast<BinaryOp*>(assign->value.get());
            if (binOp && (binOp->op.type == TokenType::PLUS || binOp->op.type == TokenType::MULTIPLY)) {
                Variable* leftVar = dynamic_cast<Variable*>(binOp->left.get());
                Variable* rightVar = dynamic_cast<Variable*>(binOp->right.get());

                if (leftVar && leftVar->name == assign->varName) {
                    if (rightVar && rightVar->name == loopVar) {
                        accumVar = assign->varName;
                        accumOp = binOp->op.type;
                        isAccumulation = true;
                    }
                } else if (rightVar && rightVar->name == assign->varName) {
                    if (leftVar && leftVar->name == loopVar) {
                        accumVar = assign->varName;
                        accumOp = binOp->op.type;
                        isAccumulation = true;
                    }
                }
            }
        }
    }

    if (!isAccumulation) return false;

    // Obtener valor inicial del acumulador
    int result;
    if (constantValues.find(accumVar) != constantValues.end()) {
        result = constantValues[accumVar];
    } else {
        // Si no hay valor inicial, asumir 0 para suma, 1 para multiplicación
        result = (accumOp == TokenType::PLUS) ? 0 : 1;
    }

    // Evaluar el loop
    for (int i = startValue; i < endValue; i += incValue) {
        if (accumOp == TokenType::PLUS) {
            result += i;
        } else if (accumOp == TokenType::MULTIPLY) {
            result *= i;
        }
    }

    string opName = (accumOp == TokenType::PLUS) ? "sum" : "product";
    cout << "    Constant loop evaluation: " << opName << " loop replaced with constant " << result << endl;

    if (initDecl) {
        output.push_back(cloneStmt(initDecl));
    }

    auto resultExpr = make_unique<IntLiteral>(result);
    resultExpr->line = forStmt->line;
    auto assignStmt = make_unique<AssignStmt>(accumVar, move(resultExpr));
    assignStmt->line = forStmt->line;
    output.push_back(move(assignStmt));

    constantValues[accumVar] = result;

    return true;
}

unique_ptr<Stmt> Optimizer::cloneStmt(Stmt* stmt) {
    if (!stmt) return nullptr;

    if (VarDecl* varDecl = dynamic_cast<VarDecl*>(stmt)) {
        unique_ptr<VarDecl> cloned;
        if (varDecl->initializer) {
            cloned = make_unique<VarDecl>(
                varDecl->type,
                varDecl->name,
                cloneExpr(varDecl->initializer.get())
            );
        } else {
            cloned = make_unique<VarDecl>(
                varDecl->type,
                varDecl->name,
                nullptr
            );
        }
        cloned->line = varDecl->line;
        return cloned;
    }

    if (AssignStmt* assign = dynamic_cast<AssignStmt*>(stmt)) {
        auto cloned = make_unique<AssignStmt>(
            assign->varName,
            cloneExpr(assign->value.get())
        );
        cloned->line = assign->line;
        return cloned;
    }

    if (Block* block = dynamic_cast<Block*>(stmt)) {
        vector<unique_ptr<Stmt>> clonedStmts;
        for (auto& s : block->statements) {
            auto cloned = cloneStmt(s.get());
            if (cloned) {
                clonedStmts.push_back(move(cloned));
            }
        }
        auto cloned = make_unique<Block>(move(clonedStmts));
        cloned->line = block->line;
        return cloned;
    }

    if (ExprStmt* exprStmt = dynamic_cast<ExprStmt*>(stmt)) {
        auto cloned = make_unique<ExprStmt>(cloneExpr(exprStmt->expression.get()));
        cloned->line = exprStmt->line;
        return cloned;
    }

    return nullptr;
}

unique_ptr<Expr> Optimizer::cloneExpr(Expr* expr) {
    if (!expr) return nullptr;

    if (IntLiteral* lit = dynamic_cast<IntLiteral*>(expr)) {
        auto cloned = make_unique<IntLiteral>(lit->value);
        cloned->line = lit->line;
        return cloned;
    }

    if (Variable* var = dynamic_cast<Variable*>(expr)) {
        if (constantValues.find(var->name) != constantValues.end()) {
            auto cloned = make_unique<IntLiteral>(constantValues[var->name]);
            cloned->line = var->line;
            return cloned;
        }
        auto cloned = make_unique<Variable>(var->name);
        cloned->line = var->line;
        return cloned;
    }

    if (BinaryOp* binOp = dynamic_cast<BinaryOp*>(expr)) {
        auto leftClone = cloneExpr(binOp->left.get());
        auto rightClone = cloneExpr(binOp->right.get());

        if (leftClone && rightClone) {
            auto cloned = make_unique<BinaryOp>(
                move(leftClone),
                binOp->op,
                move(rightClone)
            );
            cloned->line = binOp->line;
            return cloned;
        }
    }

    if (AssignExpr* assignExpr = dynamic_cast<AssignExpr*>(expr)) {
        unique_ptr<AssignExpr> cloned;
        if (assignExpr->isArrayAssign) {
            vector<unique_ptr<Expr>> clonedIndices;
            for (auto& index : assignExpr->indices) {
                clonedIndices.push_back(cloneExpr(index.get()));
            }
            cloned = make_unique<AssignExpr>(
                assignExpr->varName,
                move(clonedIndices),
                cloneExpr(assignExpr->value.get())
            );
        } else {
            cloned = make_unique<AssignExpr>(
                assignExpr->varName,
                cloneExpr(assignExpr->value.get())
            );
        }
        cloned->line = assignExpr->line;
        return cloned;
    }

    return nullptr;
}

void Optimizer::eliminateDeadStores(Block* block) {
    set<string> liveVars;
    vector<bool> isDead(block->statements.size(), false);
    
    for (int i = block->statements.size() - 1; i >= 0; i--) {
        Stmt* stmt = block->statements[i].get();
        
        if (AssignStmt* assign = dynamic_cast<AssignStmt*>(stmt)) {
            if (liveVars.find(assign->varName) == liveVars.end()) {
                isDead[i] = true;
                cout << "    Dead store eliminated: " << assign->varName << endl;
            } else {
                liveVars.erase(assign->varName);
            }
            
            getReadVariables(assign->value.get(), liveVars);
        }
        
        else if (VarDecl* varDecl = dynamic_cast<VarDecl*>(stmt)) {
            if (liveVars.find(varDecl->name) == liveVars.end()) {
                isDead[i] = true;
                cout << "    Dead variable declaration eliminated: " << varDecl->name << endl;
            } else {
                liveVars.erase(varDecl->name);
                if (varDecl->initializer) {
                    getReadVariables(varDecl->initializer.get(), liveVars);
                }
            }
        }
        
        else {
            getReadVariablesInStmt(stmt, liveVars);
        }
    }
    
    vector<unique_ptr<Stmt>> aliveStmts;
    for (size_t i = 0; i < block->statements.size(); i++) {
        if (!isDead[i]) {
            aliveStmts.push_back(move(block->statements[i]));
        }
    }
    
    block->statements = move(aliveStmts);
}

void Optimizer::getReadVariables(Expr* expr, set<string>& variables) {
    if (!expr) return;
    
    if (Variable* var = dynamic_cast<Variable*>(expr)) {
        variables.insert(var->name);
    }
    else if (BinaryOp* binOp = dynamic_cast<BinaryOp*>(expr)) {
        getReadVariables(binOp->left.get(), variables);
        getReadVariables(binOp->right.get(), variables);
    }
    else if (UnaryOp* unOp = dynamic_cast<UnaryOp*>(expr)) {
        getReadVariables(unOp->operand.get(), variables);
    }
    else if (CallExpr* call = dynamic_cast<CallExpr*>(expr)) {
        for (auto& arg : call->arguments) {
            getReadVariables(arg.get(), variables);
        }
    }
    else if (ArrayAccess* arrAccess = dynamic_cast<ArrayAccess*>(expr)) {
        variables.insert(arrAccess->arrayName);
        for (auto& index : arrAccess->indices) {
            getReadVariables(index.get(), variables);
        }
    }
    else if (TernaryExpr* ternary = dynamic_cast<TernaryExpr*>(expr)) {
        getReadVariables(ternary->condition.get(), variables);
        getReadVariables(ternary->exprTrue.get(), variables);
        getReadVariables(ternary->exprFalse.get(), variables);
    }
    else if (CastExpr* cast = dynamic_cast<CastExpr*>(expr)) {
        getReadVariables(cast->expr.get(), variables);
    }
    else if (AssignExpr* assignExpr = dynamic_cast<AssignExpr*>(expr)) {
        getReadVariables(assignExpr->value.get(), variables);
        for (auto& index : assignExpr->indices) {
            getReadVariables(index.get(), variables);
        }
    }
}

void Optimizer::getReadVariablesInStmt(Stmt* stmt, set<string>& variables) {
    if (!stmt) return;
    
    if (ExprStmt* exprStmt = dynamic_cast<ExprStmt*>(stmt)) {
        getReadVariables(exprStmt->expression.get(), variables);
    }
    else if (ReturnStmt* retStmt = dynamic_cast<ReturnStmt*>(stmt)) {
        if (retStmt->value) {
            getReadVariables(retStmt->value.get(), variables);
        }
    }
    else if (IfStmt* ifStmt = dynamic_cast<IfStmt*>(stmt)) {
        getReadVariables(ifStmt->condition.get(), variables);
        getReadVariablesInStmt(ifStmt->thenBranch.get(), variables);
        if (ifStmt->elseBranch) {
            getReadVariablesInStmt(ifStmt->elseBranch.get(), variables);
        }
    }
    else if (WhileStmt* whileStmt = dynamic_cast<WhileStmt*>(stmt)) {
        getReadVariables(whileStmt->condition.get(), variables);
        getReadVariablesInStmt(whileStmt->body.get(), variables);
    }
    else if (ForStmt* forStmt = dynamic_cast<ForStmt*>(stmt)) {
        if (forStmt->condition) {
            getReadVariables(forStmt->condition.get(), variables);
        }
        if (forStmt->increment) {
            getReadVariables(forStmt->increment.get(), variables);
        }
        getReadVariablesInStmt(forStmt->body.get(), variables);
    }
    else if (Block* block = dynamic_cast<Block*>(stmt)) {
        for (auto& s : block->statements) {
            getReadVariablesInStmt(s.get(), variables);
        }
    }
}
