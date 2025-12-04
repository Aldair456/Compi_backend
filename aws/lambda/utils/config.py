from typing import Final


COMPILER_SOURCE: Final[str] = '/var/task/compiler'
COMPILER_PATH: Final[str] = '/tmp/compiler'


WORK_DIR: Final[str] = '/tmp/compile'


INPUT_FILE: Final[str] = 'input.c'
OUTPUT_ASM: Final[str] = 'output.asm'
OUTPUT_DEBUG: Final[str] = 'output.debug.json'


MAX_EMULATION_STEPS: Final[int] = 1000
COMPILATION_TIMEOUT: Final[int] = 30


CORS_HEADERS: Final[dict] = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json'
}

