import json
from typing import Dict, Any, List


def generate_visualizer_html(debug_data: Dict[str, Any], 
                           execution_snapshots: List[Dict[str, Any]],
                           source_file: str = "input.c") -> str:
    
    source_lines = debug_data.get('sourceLines', [])
    instructions = debug_data.get('instructions', [])
    
    steps_data = []
    for i, snapshot in enumerate(execution_snapshots):
        inst_data = snapshot.get('instruction', {})
        inst_id = inst_data.get('id', i)
        
        if inst_id < len(instructions):
            inst_info = instructions[inst_id]
            c_line = inst_info.get('sourceLine', 0)
            c_code = inst_info.get('cCode', '')
            if not c_code and c_line > 0 and c_line <= len(source_lines):
                c_code = source_lines[c_line - 1].strip()
        else:
            c_line = inst_data.get('sourceLine', 0)
            c_code = ''
        
        asm_inst = inst_data.get('assembly', '').strip()
        if not asm_inst:
            continue
        
        registers = snapshot.get('registers', {})
        stack_data = snapshot.get('stack', [])
        variables = {}
        
        call_stack = snapshot.get('callStack', [])
        if call_stack:
            active_frame = call_stack[-1]
            frame_vars = active_frame.get('variables', {})
            for var_name, var_info in frame_vars.items():
                variables[var_name] = {
                    'type': var_info.get('type', 'int'),
                    'value': var_info.get('value', 0),
                    'location': f"stack:{var_info.get('address', 'unknown')}"
                }
        
        step_info = {
            'step': i,
            'c_line': c_line,
            'c_code': c_code,
            'asm_line': i + 1,
            'asm_instruction': asm_inst.split('\n')[0] if asm_inst else '',
            'registers': {},
            'stack': [],
            'variables': variables
        }
        
        for reg_name in ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp']:
            if reg_name in registers:
                reg_info = registers[reg_name]
                step_info['registers'][reg_name] = reg_info.get('hex', '0x0')
        
        for stack_item in stack_data[:20]:
            step_info['stack'].append({
                'address': stack_item.get('address', '0x0'),
                'value': stack_item.get('value', '0x0'),
                'label': stack_item.get('variable', '')
            })
        
        steps_data.append(step_info)
    
    metadata = {
        'source_file': source_file,
        'steps': steps_data
    }
    
    metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
    source_lines_json = json.dumps(source_lines, ensure_ascii=False)
    instructions_json = json.dumps(instructions, ensure_ascii=False)
    
    html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visualizador de Ejecución</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
            overflow: hidden;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
            flex-direction: column;
        }}
        
        .header {{
            background: #252526;
            padding: 10px 20px;
            border-bottom: 1px solid #3e3e42;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .controls {{
            display: flex;
            gap: 10px;
        }}
        
        button {{
            background: #0e639c;
            color: white;
            border: none;
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 14px;
        }}
        
        button:hover {{
            background: #1177bb;
        }}
        
        button:disabled {{
            background: #3e3e42;
            cursor: not-allowed;
        }}
        
        .step-info {{
            color: #cccccc;
            font-size: 14px;
        }}
        
        .panels {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}
        
        .panel {{
            flex: 1;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #3e3e42;
            overflow: hidden;
        }}
        
        .panel:last-child {{
            border-right: none;
        }}
        
        .panel-title {{
            background: #2d2d30;
            padding: 8px 15px;
            font-weight: bold;
            border-bottom: 1px solid #3e3e42;
            font-size: 13px;
        }}
        
        .code-container {{
            flex: 1;
            overflow: auto;
            padding: 10px;
        }}
        
        .code-line {{
            padding: 2px 5px;
            white-space: pre;
            font-size: 13px;
            line-height: 1.6;
        }}
        
        .code-line.highlight {{
            background: #264f78;
            color: #ffffff;
        }}
        
        .registers-container {{
            padding: 10px;
            overflow-y: auto;
        }}
        
        .register-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 10px;
            margin: 3px 0;
            background: #252526;
            border-radius: 3px;
        }}
        
        .register-name {{
            font-weight: bold;
            color: #4ec9b0;
        }}
        
        .register-value {{
            color: #ce9178;
            font-family: monospace;
        }}
        
        .stack-container {{
            padding: 10px;
            overflow-y: auto;
        }}
        
        .stack-item {{
            padding: 8px;
            margin: 5px 0;
            background: #252526;
            border-left: 3px solid #0e639c;
            border-radius: 3px;
        }}
        
        .stack-address {{
            color: #4ec9b0;
            font-size: 12px;
        }}
        
        .stack-value {{
            color: #ce9178;
            font-family: monospace;
            margin-top: 3px;
        }}
        
        .stack-label {{
            color: #dcdcaa;
            font-size: 11px;
            margin-top: 3px;
        }}
        
        .variables-container {{
            padding: 10px;
            overflow-y: auto;
        }}
        
        .variable-item {{
            padding: 8px;
            margin: 5px 0;
            background: #252526;
            border-radius: 3px;
        }}
        
        .variable-name {{
            color: #4ec9b0;
            font-weight: bold;
        }}
        
        .variable-value {{
            color: #ce9178;
            font-family: monospace;
            margin-top: 3px;
        }}
        
        .variable-type {{
            color: #569cd6;
            font-size: 11px;
            margin-top: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="step-info">
                Paso: <span id="current-step">0</span> / <span id="total-steps">0</span>
            </div>
            <div class="controls">
                <button id="btn-reset">Reset</button>
                <button id="btn-prev">◀ Anterior</button>
                <button id="btn-next">Siguiente ▶</button>
                <button id="btn-run">▶▶ Ejecutar Todo</button>
            </div>
        </div>
        <div class="panels">
            <div class="panel">
                <div class="panel-title">Código C</div>
                <div class="code-container" id="c-code"></div>
            </div>
            <div class="panel">
                <div class="panel-title">Código Ensamblador</div>
                <div class="code-container" id="asm-code"></div>
            </div>
            <div class="panel">
                <div class="panel-title">Estado (Registros + Stack)</div>
                <div style="display: flex; flex-direction: column; height: 100%;">
                    <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
                        <div class="panel-title" style="font-size: 11px;">Registros</div>
                        <div class="registers-container" id="registers"></div>
                    </div>
                    <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column; border-top: 1px solid #3e3e42;">
                        <div class="panel-title" style="font-size: 11px;">Stack</div>
                        <div class="stack-container" id="stack"></div>
                    </div>
                    <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column; border-top: 1px solid #3e3e42;">
                        <div class="panel-title" style="font-size: 11px;">Variables</div>
                        <div class="variables-container" id="variables"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const metadata = ''' + metadata_json + ''';
        let currentStep = 0;
        let isRunning = false;
        let runInterval = null;
        
        const sourceLines = ''' + source_lines_json + ''';
        const instructions = ''' + instructions_json + ''';
        
        function initVisualizer() {{
            document.getElementById('total-steps').textContent = metadata.steps.length;
            renderStep(0);
            setupControls();
        }}
        
        function setupControls() {{
            document.getElementById('btn-reset').addEventListener('click', () => {{
                currentStep = 0;
                if (runInterval) {{
                    clearInterval(runInterval);
                    isRunning = false;
                    runInterval = null;
                }}
                renderStep(0);
            }});
            
            document.getElementById('btn-prev').addEventListener('click', () => {{
                if (currentStep > 0) {{
                    currentStep--;
                    renderStep(currentStep);
                }}
            }});
            
            document.getElementById('btn-next').addEventListener('click', () => {{
                if (currentStep < metadata.steps.length - 1) {{
                    currentStep++;
                    renderStep(currentStep);
                }}
            }});
            
            document.getElementById('btn-run').addEventListener('click', () => {{
                if (isRunning) {{
                    clearInterval(runInterval);
                    isRunning = false;
                    runInterval = null;
                    document.getElementById('btn-run').textContent = '▶▶ Ejecutar Todo';
                }} else {{
                    isRunning = true;
                    document.getElementById('btn-run').textContent = '⏸ Pausar';
                    runInterval = setInterval(() => {{
                        if (currentStep < metadata.steps.length - 1) {{
                            currentStep++;
                            renderStep(currentStep);
                        }} else {{
                            clearInterval(runInterval);
                            isRunning = false;
                            runInterval = null;
                            document.getElementById('btn-run').textContent = '▶▶ Ejecutar Todo';
                        }}
                    }}, 500);
                }}
            }});
        }}
        
        function renderStep(stepIndex) {{
            if (stepIndex < 0 || stepIndex >= metadata.steps.length) return;
            
            const step = metadata.steps[stepIndex];
            currentStep = stepIndex;
            
            document.getElementById('current-step').textContent = stepIndex;
            
            renderCCode(step.c_line);
            renderAsmCode(step.asm_line);
            renderRegisters(step.registers);
            renderStack(step.stack);
            renderVariables(step.variables);
            
            updateButtons();
        }}
        
        function renderCCode(highlightLine) {{
            const container = document.getElementById('c-code');
            container.innerHTML = '';
            
            sourceLines.forEach((line, index) => {{
                const lineDiv = document.createElement('div');
                lineDiv.className = 'code-line';
                lineDiv.textContent = (index + 1) + ': ' + line;
                
                if (index + 1 === highlightLine) {{
                    lineDiv.classList.add('highlight');
                }}
                
                container.appendChild(lineDiv);
            }});
        }}
        
        function renderAsmCode(highlightLine) {{
            const container = document.getElementById('asm-code');
            container.innerHTML = '';
            
            instructions.forEach((inst, index) => {{
                const asm = inst.assembly || '';
                const lineDiv = document.createElement('div');
                lineDiv.className = 'code-line';
                lineDiv.textContent = (index + 1) + ': ' + asm.split('\\n')[0];
                
                if (index + 1 === highlightLine) {{
                    lineDiv.classList.add('highlight');
                }}
                
                container.appendChild(lineDiv);
            }});
        }}
        
        function renderRegisters(registers) {{
            const container = document.getElementById('registers');
            container.innerHTML = '';
            
            const regOrder = ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp'];
            
            regOrder.forEach(regName => {{
                if (registers[regName]) {{
                    const regDiv = document.createElement('div');
                    regDiv.className = 'register-item';
                    
                    const nameSpan = document.createElement('span');
                    nameSpan.className = 'register-name';
                    nameSpan.textContent = regName;
                    
                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'register-value';
                    valueSpan.textContent = registers[regName];
                    
                    regDiv.appendChild(nameSpan);
                    regDiv.appendChild(valueSpan);
                    container.appendChild(regDiv);
                }}
            }});
        }}
        
        function renderStack(stack) {{
            const container = document.getElementById('stack');
            container.innerHTML = '';
            
            if (stack.length === 0) {{
                container.innerHTML = '<div style="color: #808080; padding: 10px;">Stack vacío</div>';
                return;
            }}
            
            stack.forEach(item => {{
                const stackDiv = document.createElement('div');
                stackDiv.className = 'stack-item';
                
                const addrDiv = document.createElement('div');
                addrDiv.className = 'stack-address';
                addrDiv.textContent = item.address;
                
                const valueDiv = document.createElement('div');
                valueDiv.className = 'stack-value';
                valueDiv.textContent = item.value;
                
                stackDiv.appendChild(addrDiv);
                stackDiv.appendChild(valueDiv);
                
                if (item.label) {{
                    const labelDiv = document.createElement('div');
                    labelDiv.className = 'stack-label';
                    labelDiv.textContent = '→ ' + item.label;
                    stackDiv.appendChild(labelDiv);
                }}
                
                container.appendChild(stackDiv);
            }});
        }}
        
        function renderVariables(variables) {{
            const container = document.getElementById('variables');
            container.innerHTML = '';
            
            if (Object.keys(variables).length === 0) {{
                container.innerHTML = '<div style="color: #808080; padding: 10px;">No hay variables visibles</div>';
                return;
            }}
            
            Object.keys(variables).forEach(varName => {{
                const varInfo = variables[varName];
                const varDiv = document.createElement('div');
                varDiv.className = 'variable-item';
                
                const nameDiv = document.createElement('div');
                nameDiv.className = 'variable-name';
                nameDiv.textContent = varName;
                
                const valueDiv = document.createElement('div');
                valueDiv.className = 'variable-value';
                valueDiv.textContent = varInfo.value;
                
                const typeDiv = document.createElement('div');
                typeDiv.className = 'variable-type';
                typeDiv.textContent = varInfo.type + ' @ ' + varInfo.location;
                
                varDiv.appendChild(nameDiv);
                varDiv.appendChild(valueDiv);
                varDiv.appendChild(typeDiv);
                container.appendChild(varDiv);
            }});
        }}
        
        function updateButtons() {{
            document.getElementById('btn-prev').disabled = (currentStep === 0);
            document.getElementById('btn-next').disabled = (currentStep >= metadata.steps.length - 1);
        }}
        
        window.addEventListener('load', initVisualizer);
    </script>
</body>
</html>'''
    
    return html_content

