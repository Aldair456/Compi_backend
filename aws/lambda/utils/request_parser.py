import json
from typing import Dict, Any, Tuple


class RequestParser:
    @staticmethod
    def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
        if 'body' in event:
            if isinstance(event['body'], str):
                return json.loads(event['body'])
            return event['body']
        return event
    @staticmethod
    def extract_source_code(body: Dict[str, Any]) -> str:
        source_code = body.get('source', '')
        if not source_code:
            raise ValueError('No source code provided')
        return source_code
    @staticmethod
    def extract_flags(body: Dict[str, Any]) -> Tuple[bool, bool]:
        debug_mode = body.get('debug', False)
        optimize_mode = body.get('optimize', False)
        return debug_mode, optimize_mode
    @staticmethod
    def validate_request(event: Dict[str, Any]) -> Tuple[str, bool, bool]:
        body = RequestParser.parse_body(event)
        source_code = RequestParser.extract_source_code(body)
        debug_mode, optimize_mode = RequestParser.extract_flags(body)
        return source_code, debug_mode, optimize_mode

