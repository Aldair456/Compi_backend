import json
from typing import Dict, Any

from ..services.compilation_service import CompilationService


_service = CompilationService()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler que procesa solicitudes de compilación.
    
    Returns:
        Dict con estructura de respuesta HTTP para API Gateway:
        {
            'statusCode': int,  # 200 (éxito), 400 (error cliente), 408 (timeout), 500 (error servidor)
            'headers': dict,    # Headers CORS y Content-Type
            'body': str         # JSON stringificado con los datos de respuesta
        }
        
    Respuestas posibles:
    
    1. Éxito (statusCode: 200):
       - Modo normal (sin visualize_mode):
         {
           'success': True,
           'assembly': str,              # Código assembly generado
           'debug': {                    # Datos de debug
             'sourceLines': [...],
             'instructions': [...],
             'stackFrame': [...]
           },
           'stats': {
             'assemblySize': int,
             'instructionsCount': int,
             'stackFrameSize': int,
             'sourceLines': int,
             'executionSteps': int (si hay ejecución)
           },
           'execution': [...] (opcional, solo si debug_mode=True)
         }
       
       - Modo visualización (con visualize_mode):
         {
           'success': True,
           'visualization': {
             'source_file': str,
             'steps': [
               {
                 'step': int,
                 'c_line': int,
                 'c_code': str,
                 'asm_line': int,
                 'asm_instruction': str,
                 'registers': {...},
                 'stack': [...],
                 'variables': {...},
                 'stackFrame': {...}
               }
             ]
           },
           'assembly': {
             'lines': [...],
             'total_lines': int,
             'content': str
           }
         }
    
    2. Error de compilación (statusCode: 400):
       {
         'error': 'Compilation failed',
         'success': False,
         'stderr': str,
         'stdout': str
       }
    
    3. Timeout (statusCode: 408):
       {
         'error': 'Compilation timeout (30s)',
         'success': False
       }
    
    4. Error de validación (statusCode: 400):
       {
         'error': str,  # Mensaje de error de validación
         'success': False
       }
    
    5. Error interno (statusCode: 500):
       {
         'error': str,      # Mensaje de error
         'success': False,
         'trace': str       # Stack trace (opcional)
       }
    """
    print("===== EVENT DEBUG =====")
    print(json.dumps(event, indent=2))
    print("=====================")
    return _service.process_request(event)

