import json
from typing import Dict, Any

from ..services.compilation_service import CompilationService



_service = CompilationService()



def lambda_handler(event: Dict[str, Any],context :any):
    valor_de_cosa=event.gey 
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    print("===== EVENT DEBUG =====")
    print(json.dumps(event, indent=2))
    print("=====================")
    return _service.process_request(event)

