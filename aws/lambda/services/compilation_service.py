import traceback
from typing import Dict, Any

from ..core.compiler import CompilerManager
from ..core.emulator import emulate_from_debug
from ..utils.config import MAX_EMULATION_STEPS, WORK_DIR, INPUT_FILE
from ..utils.response import ResponseBuilder
from ..utils.request_parser import RequestParser
import os

  
class CompilationService:
    def __init__(self):
        self.compiler = CompilerManager()
        self.response_builder = ResponseBuilder()
        self.request_parser = RequestParser()
    def process_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            source_code, debug_mode, optimize_mode, visualize_mode = self.request_parser.validate_request(event)
            print(f"Received source code ({len(source_code)} chars)")
            print(f"Debug mode: {debug_mode}, Optimize mode: {optimize_mode}, Visualize mode: {visualize_mode}")
            self.compiler.ensure_compiler_ready()
            success, stdout, stderr = self.compiler.compile(
                source_code,
                debug_mode,
                optimize_mode,
                visualize_mode
            )
            if not success:
                return self.response_builder.compilation_failed(stderr or '', stdout or '')
            asm_content = self.compiler.read_assembly_output()
            debug_data = self.compiler.read_debug_output(source_code)
            execution_snapshots = []
            if debug_mode:
                execution_snapshots = self._run_emulation(debug_data)
            
            if visualize_mode:
                visualization_json = self._generate_visualization_json(debug_data, execution_snapshots, asm_content)
                return self._build_visualization_response(visualization_json, asm_content)
            
            return self._build_success_response(
                asm_content,
                debug_data,
                execution_snapshots
            )
        except ValueError as e:
            return self.response_builder.error(str(e), status_code=400)
        except TimeoutError as e:
            return self.response_builder.timeout_error(30)
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error: {str(e)}")
            print(error_trace)
            return self.response_builder.internal_error(e, error_trace)
    def _run_emulation(self, debug_data: Dict[str, Any]) -> list:
        try:
            print("Starting x86-64 emulation...")
            execution_snapshots = emulate_from_debug(debug_data, max_steps=MAX_EMULATION_STEPS)
            print(f"Execution snapshots generated: {len(execution_snapshots)} steps")
            return execution_snapshots
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Emulation failed: {str(e)}")
            print(error_trace)
            return []
    def _build_asm_executable_map(self, asm_content: str) -> Dict[int, int]:
        """
        Construye un mapa de índices de instrucciones ejecutables a líneas del assembler.
        Retorna un dict que mapea: {índice_secuencial: número_línea_real}
        """
        if not asm_content:
            return {}
        
        asm_lines = asm_content.split('\n')
        executable_map = {}
        exec_index = 0
        
        for line_num, line in enumerate(asm_lines, start=1):
            line_stripped = line.strip()
            
            # Saltar líneas vacías
            if not line_stripped:
                continue
            
            # Saltar comentarios
            if line_stripped.startswith(';'):
                continue
            
            # Saltar directivas de sección y declaraciones
            if line_stripped.startswith('.section') or \
               line_stripped.startswith('.extern') or \
               line_stripped.startswith('.global') or \
               line_stripped.startswith('fmt_') or \
               line_stripped.startswith('.note'):
                continue
            
            # Saltar labels solos (líneas que solo tienen un label y terminan en :)
            # Pero incluir líneas que tienen label + instrucción (ej: "main: pushq %rbp")
            if line_stripped.endswith(':') and ':' in line_stripped:
                # Si solo es un label sin instrucción después, saltarlo
                parts = line_stripped.split(':')
                if len(parts) == 2 and not parts[1].strip():
                    continue
            
            # Es una instrucción ejecutable (o tiene una instrucción)
            # Extraer la parte de la instrucción si hay un label
            if ':' in line_stripped:
                # Hay un label, tomar la parte después del :
                instruction_part = line_stripped.split(':', 1)[1].strip()
                if instruction_part:
                    # Hay instrucción después del label
                    executable_map[exec_index] = line_num
                    exec_index += 1
            else:
                # No hay label, es directamente una instrucción
                executable_map[exec_index] = line_num
                exec_index += 1
        
        return executable_map
    
    def _find_asm_line_by_index(self, asm_content: str, instruction_index: int) -> int:
        """
        Encuentra la línea real en el assembler usando el índice secuencial de instrucciones ejecutables.
        """
        executable_map = self._build_asm_executable_map(asm_content)
        return executable_map.get(instruction_index, 0)
    
    def _generate_visualization_json(self, debug_data: Dict[str, Any], 
                                     execution_snapshots: list,
                                     asm_content: str = '') -> Dict[str, Any]:
        source_lines = debug_data.get('sourceLines', [])
        instructions = debug_data.get('instructions', [])
        source_file = INPUT_FILE
        
        # Construir mapa de instrucciones ejecutables a líneas del assembler
        executable_map = self._build_asm_executable_map(asm_content) if asm_content else {}
        
        steps_data = []
        for i, snapshot in enumerate(execution_snapshots):
            inst_data = snapshot.get('instruction', {})
            inst_id = inst_data.get('id', i)
            
            if inst_id >= 0 and inst_id < len(instructions):
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
            
            asm_lines = asm_inst.split('\n')
            asm_instruction = asm_lines[0] if asm_lines else asm_inst
            
            # Calcular la línea real en el assembler usando el índice secuencial
            if executable_map and inst_id in executable_map:
                # Usar el índice de la instrucción para encontrar la línea real
                asm_line = executable_map[inst_id]
            elif asm_content:
                # Fallback: intentar buscar por índice
                asm_line = self._find_asm_line_by_index(asm_content, inst_id)
            else:
                # Fallback: usar inst_id + offset estimado si no hay contenido del assembler
                # Aproximadamente 10 líneas de headers antes de las instrucciones ejecutables
                asm_line = inst_id + 11
            
            registers = snapshot.get('registers', {})
            stack_data = snapshot.get('stack', [])
            variables = {}
            
            call_stack = snapshot.get('callStack', [])
            if call_stack:
                active_frame = call_stack[-1]
                frame_vars = active_frame.get('variables', {})
                for var_name, var_info in frame_vars.items():
                    var_value = var_info.get('value', 0)
                    var_type = var_info.get('type', 'int')
                    var_location = var_info.get('address', 'unknown')
                    
                    if 'register' in var_location.lower() or 'eax' in var_location.lower() or 'rax' in var_location.lower():
                        location = f"register:{var_location.split(':')[-1] if ':' in var_location else 'eax'}"
                    else:
                        location = f"stack:{var_location}"
                    
                    variables[var_name] = {
                        'type': var_type,
                        'value': var_value,
                        'location': location
                    }
            
            step_registers = {}
            for reg_name in ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp']:
                if reg_name in registers:
                    reg_info = registers[reg_name]
                    hex_value = reg_info.get('hex', '0x0')
                    step_registers[reg_name] = hex_value
            
            step_stack = []
            for stack_item in stack_data[:50]:
                step_stack.append({
                    'address': stack_item.get('address', '0x0'),
                    'value': stack_item.get('value', '0x0'),
                    'label': stack_item.get('variable', '')
                })
            
            # Obtener stackFrame del snapshot
            stack_frame = snapshot.get('stackFrame', {})
            
            # Obtener descripción detallada de la instrucción
            instruction_description = snapshot.get('instructionDescription', {})
            
            step_info = {
                'step': i,
                'c_line': c_line,
                'c_code': c_code,
                'asm_line': asm_line,
                'asm_instruction': asm_instruction,
                'registers': step_registers,
                'stack': step_stack,
                'variables': variables,
                'stackFrame': stack_frame,
                'instructionDescription': instruction_description
            }
            
            steps_data.append(step_info)
        
        visualization_data = {
            'source_file': source_file,
            'steps': steps_data
        }
        
        return visualization_data
    
    def _build_visualization_response(self, visualization_json: Dict[str, Any], 
                                     asm_content: str) -> Dict[str, Any]:
        asm_lines = asm_content.split('\n')
        asm_json = {
            'lines': asm_lines,
            'total_lines': len(asm_lines),
            'content': asm_content
        }
        
        return self.response_builder.success({
            'success': True,
            'visualization': visualization_json,
            'assembly': asm_json
        })
    
    def _build_success_response(self, asm_content: str, debug_data: Dict[str, Any],
                                execution_snapshots: list) -> Dict[str, Any]:
        response_data = {
            'success': True,
            'assembly': asm_content,
            'debug': debug_data,
            'stats': {
                'assemblySize': len(asm_content),
                'instructionsCount': len(debug_data.get('instructions', [])),
                'stackFrameSize': len(debug_data.get('stackFrame', [])),
                'sourceLines': len(debug_data.get('sourceLines', []))
            }
        }
        if execution_snapshots:
            response_data['execution'] = execution_snapshots
            response_data['stats']['executionSteps'] = len(execution_snapshots)
        return self.response_builder.success(response_data)

