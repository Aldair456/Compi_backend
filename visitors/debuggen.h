#ifndef DEBUGGEN_H
#define DEBUGGEN_H

#include <string>
#include <vector>
#include <fstream>
#include <sstream>

using namespace std;

struct DebugInstruction {
    int id;
    string assembly;
    int sourceLine;
    string cCode;
    string varName;
    string description;
};

struct StackFrameInfo {
    string varName;
    int offset;
    string type;
    bool isArray;
    int sourceLine;
};

class DebugGen {
private:
    vector<DebugInstruction> instructions;
    int instructionCounter;
    string sourceCode;
    vector<string> sourceLines;
    vector<StackFrameInfo> stackFrames;
public:
    DebugGen();
    void setSourceCode(const string& source);
    void logInstruction(const string& assembly, int sourceLine,
                       const string& varName = "",
                       const string& description = "",
                       const string& cCode = "");
    void logStackVariable(const string& varName, int offset,
                         const string& type, bool isArray, int sourceLine);
    void clearStackFrame();
    void generateJSON(const string& filename);
    string getJSON();
};

#endif
