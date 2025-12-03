import traceback
from typing import Dict, Any

from ..core.compiler import CompilerManager
from ..core.emulator import emulate_from_debug
from ..utils.config import MAX_EMULATION_STEPS
from ..utils.response import ResponseBuilder
from ..utils.request_parser import RequestParser


class CompilationService:
    def __init__(self):
        self.compiler = CompilerManager()
        self.response_builder = ResponseBuilder()
        self.request_parser = RequestParser()
    def process_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            source_code, debug_mode, optimize_mode = self.request_parser.validate_request(event)
            print(f"Received source code ({len(source_code)} chars)")
            print(f"Debug mode: {debug_mode}, Optimize mode: {optimize_mode}")
            self.compiler.ensure_compiler_ready()
            success, stdout, stderr = self.compiler.compile(
                source_code,
                debug_mode,
                optimize_mode
            )
            if not success:
                return self.response_builder.compilation_failed(stderr or '', stdout or '')
            asm_content = self.compiler.read_assembly_output()
            debug_data = self.compiler.read_debug_output(source_code)
            execution_snapshots = []
            if debug_mode:
                execution_snapshots = self._run_emulation(debug_data)
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

