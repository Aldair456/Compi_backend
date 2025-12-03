#include "debuggen.h"
#include <iostream>
#include <sstream>

static string escapeJSON(const string& str) {
    stringstream escaped;
    for (char c : str) {
        if (c == '"') escaped << "\\\"";
        else if (c == '\\') escaped << "\\\\";
        else if (c == '\n') escaped << "\\n";
        else if (c == '\r') escaped << "\\r";
        else if (c == '\t') escaped << "\\t";
        else escaped << c;
    }
    return escaped.str();
}

DebugGen::DebugGen() : instructionCounter(0) {}

void DebugGen::setSourceCode(const string& source) {
    sourceCode = source;
    sourceLines.clear();
    stringstream ss(source);
    string line;
    while (getline(ss, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        sourceLines.push_back(line);
    }
}

void DebugGen::logInstruction(const string& assembly, int sourceLine,
                             const string& varName,
                             const string& description) {
    DebugInstruction inst;
    inst.id = instructionCounter++;
    inst.assembly = assembly;
    inst.sourceLine = sourceLine;
    inst.varName = varName;
    inst.description = description;
    instructions.push_back(inst);
}

void DebugGen::logStackVariable(const string& varName, int offset,
                               const string& type, bool isArray, int sourceLine) {
    StackFrameInfo frame;
    frame.varName = varName;
    frame.offset = offset;
    frame.type = type;
    frame.isArray = isArray;
    frame.sourceLine = sourceLine;
    stackFrames.push_back(frame);
}

void DebugGen::clearStackFrame() {
    stackFrames.clear();
}

string DebugGen::getJSON() {
    stringstream json;
    json << "{\n";
    json << "  \"sourceLines\": [\n";
    for (size_t i = 0; i < sourceLines.size(); i++) {
        json << "    \"" << escapeJSON(sourceLines[i]) << "\"";
        if (i < sourceLines.size() - 1) json << ",";
        json << "\n";
    }
    json << "  ],\n";
    json << "  \"stackFrame\": [\n";
    for (size_t i = 0; i < stackFrames.size(); i++) {
        const auto& frame = stackFrames[i];
        json << "    {\n";
        json << "      \"varName\": \"" << escapeJSON(frame.varName) << "\",\n";
        json << "      \"offset\": " << frame.offset << ",\n";
        json << "      \"type\": \"" << escapeJSON(frame.type) << "\",\n";
        json << "      \"isArray\": " << (frame.isArray ? "true" : "false") << ",\n";
        json << "      \"sourceLine\": " << frame.sourceLine << "\n";
        json << "    }";
        if (i < stackFrames.size() - 1) json << ",";
        json << "\n";
    }
    json << "  ],\n";
    json << "  \"instructions\": [\n";
    for (size_t i = 0; i < instructions.size(); i++) {
        const auto& inst = instructions[i];
        json << "    {\n";
        json << "      \"id\": " << inst.id << ",\n";
        json << "      \"assembly\": \"" << escapeJSON(inst.assembly) << "\",\n";
        json << "      \"sourceLine\": " << inst.sourceLine << ",\n";
        if (!inst.varName.empty()) {
            json << "      \"varName\": \"" << escapeJSON(inst.varName) << "\",\n";
        }
        if (!inst.description.empty()) {
            json << "      \"description\": \"" << escapeJSON(inst.description) << "\",\n";
        }
        json << "      \"line\": " << inst.sourceLine << "\n";
        json << "    }";
        if (i < instructions.size() - 1) json << ",";
        json << "\n";
    }
    json << "  ]\n";
    json << "}\n";
    return json.str();
}

void DebugGen::generateJSON(const string& filename) {
    ofstream file(filename);
    if (!file.is_open()) {
        cerr << "Error: Could not open debug file " << filename << endl;
        return;
    }
    file << getJSON();
    file.close();
}

