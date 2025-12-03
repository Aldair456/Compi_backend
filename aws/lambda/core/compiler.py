import os
import shutil
import subprocess
import json
from typing import Dict, Optional, Tuple
from ..utils.config import (
    COMPILER_SOURCE, COMPILER_PATH, WORK_DIR,
    INPUT_FILE, OUTPUT_ASM, OUTPUT_DEBUG, COMPILATION_TIMEOUT
)


class CompilerManager:
    def __init__(self):
        self.compiler_path = COMPILER_PATH
        self.compiler_source = COMPILER_SOURCE
    def ensure_compiler_ready(self) -> None:
        print(f"Copying compiler from {self.compiler_source} to {self.compiler_path}")
        if not os.path.exists(self.compiler_source):
            raise FileNotFoundError(f"Compiler source not found at {self.compiler_source}")
        shutil.copy2(self.compiler_source, self.compiler_path)
        os.chmod(self.compiler_path, 0o755)
        print(f"Compiler ready at {self.compiler_path}")
    def prepare_work_directory(self) -> None:
        os.makedirs(WORK_DIR, exist_ok=True)
    def save_source_code(self, source_code: str) -> str:
        input_file = os.path.join(WORK_DIR, INPUT_FILE)
        with open(input_file, 'w') as f:
            f.write(source_code)
        print(f"Saved to {input_file}")
        return input_file
    def build_compiler_command(self, input_file: str, debug_mode: bool,
                               optimize_mode: bool) -> list:
        cmd = [self.compiler_path, input_file, os.path.join(WORK_DIR, OUTPUT_ASM)]
        if debug_mode:
            cmd.append('--debug')
        if optimize_mode:
            cmd.append('--optimize')
            print("Optimization enabled - line-by-line debug may be affected")
        return cmd
    def compile(self, source_code: str, debug_mode: bool,
                optimize_mode: bool) -> Tuple[bool, Optional[str], Optional[str]]:
        self.prepare_work_directory()
        input_file = self.save_source_code(source_code)
        cmd = self.build_compiler_command(input_file, debug_mode, optimize_mode)
        print(f"Executing: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=COMPILATION_TIMEOUT,
                cwd=WORK_DIR
            )
            if result.returncode != 0:
                return False, result.stdout, result.stderr
            print("Compilation successful")
            return True, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise TimeoutError(f'Compilation timeout ({COMPILATION_TIMEOUT}s)')
    def read_assembly_output(self) -> str:
        output_asm = os.path.join(WORK_DIR, OUTPUT_ASM)
        with open(output_asm, 'r') as f:
            return f.read()
    def read_debug_output(self, source_code: str) -> Dict:
        output_debug = os.path.join(WORK_DIR, OUTPUT_DEBUG)
        if os.path.exists(output_debug):
            with open(output_debug, 'r') as f:
                return json.load(f)
        else:
            return {
                'sourceLines': source_code.split('\n'),
                'stackFrame': [],
                'instructions': []
            }

