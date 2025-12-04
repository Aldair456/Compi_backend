#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include "scanner/scanner.h"
#include "parser/parser.h"
#include "visitors/codegen.h"
#include "visitors/optimizer.h"
#include "visitors/debuggen.h"

using namespace std;


string readFile(const string& filename) {
    ifstream file(filename);
    if (!file.is_open()) {
        cerr << "Error: No se pudo abrir el archivo " << filename << endl;
        exit(1);
    }
    stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}


void writeFile(const string& filename, const string& content) {
    ofstream file(filename);
    if (!file.is_open()) {
        cerr << "Error: No se pudo crear el archivo " << filename << endl;
        exit(1);
    }
    file << content;
    file.close();
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        cerr << "Uso: " << argv[0] << " <archivo_entrada.c> <archivo_salida.asm> [--debug] [--optimize] [--debug-visualize]" << endl;
        cerr << "  --debug    : Genera archivo debug.json para ejecución paso a paso" << endl;
        cerr << "  --optimize  : Activa optimizaciones del compilador" << endl;
        cerr << "  --debug-visualize : Genera metadata completa para visualizador HTML" << endl;
        cerr << "  Nota: Por defecto NO se optimiza (para preservar debug línea por línea)" << endl;
        return 1;
    }
    string inputFile = argv[1];
    string outputFile = argv[2];
    bool debugMode = false;
    bool optimizeMode = false;
    bool visualizeMode = false;
    for (int i = 3; i < argc; i++) {
        string arg = argv[i];
        if (arg == "--debug") {
            debugMode = true;
        } else if (arg == "--optimize") {
            optimizeMode = true;
        } else if (arg == "--debug-visualize") {
            visualizeMode = true;
            debugMode = true;
        }
    }
    string source = readFile(inputFile);
    Scanner scanner(source);
    vector<Token> tokens = scanner.scanTokens();
    Parser parser(tokens);
    unique_ptr<Program> ast = parser.parse();
    if (!ast) {
        cerr << "Error: Fallo en el parsing" << endl;
        return 1;
    }
    if (optimizeMode) {
        cout << "🔧 Optimization mode: ENABLED" << endl;
        Optimizer optimizer;
        optimizer.optimize(ast.get());
    } else {
        cout << "🔍 Optimization mode: DISABLED (preserving line-by-line debug experience)" << endl;
    }
    CodeGen codegen;
    DebugGen debugGen;
    if (debugMode) {
        debugGen.setSourceCode(source);
        codegen.setSourceCode(source);
        codegen.setDebugGen(&debugGen);
    }
    codegen.generate(ast.get());
    string asmCode = codegen.getOutput();
    writeFile(outputFile, asmCode);
    if (debugMode) {
        debugGen.generateJSON("output.debug.json");
    }
    return 0;
}

