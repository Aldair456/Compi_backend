import re
from typing import Dict, List, Tuple, Any, Optional, Union
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class X86Emulator:
    REGISTERS_64BIT = ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
                       'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']
    REGISTERS_32BIT = ['eax', 'ebx', 'ecx', 'edx', 'edi', 'esi', 'r8d', 'r9d']
    REGISTERS_8BIT = ['al', 'bl', 'cl', 'dl', 'r8b', 'r9b', 'ah', 'bh', 'ch', 'dh']
    INITIAL_STACK_POINTER = 0x7fffffffe000
    def __init__(self):
        self.regs: Dict[str, int] = {
            reg: 0 for reg in self.REGISTERS_64BIT
        }
        self.regs['rsp'] = self.INITIAL_STACK_POINTER
        self.regs['rbp'] = self.INITIAL_STACK_POINTER
        self.flags: Dict[str, int] = {'ZF': 0, 'SF': 0, 'CF': 0, 'OF': 0}
        self.stack: Dict[int, int] = {}
        self.labels: Dict[str, int] = {}
        self.call_stack: List[Dict[str, Any]] = []
        self.function_frames: Dict[str, List[Dict[str, Any]]] = {}
    def get_reg(self, name: str) -> int:
        if name in self.regs:
            return self.regs[name]
        if name == 'eax':
            return self.regs['rax'] & 0xFFFFFFFF
        elif name == 'ebx':
            return self.regs['rbx'] & 0xFFFFFFFF
        elif name == 'ecx':
            return self.regs['rcx'] & 0xFFFFFFFF
        elif name == 'edx':
            return self.regs['rdx'] & 0xFFFFFFFF
        elif name == 'edi':
            return self.regs['rdi'] & 0xFFFFFFFF
        elif name == 'esi':
            return self.regs['rsi'] & 0xFFFFFFFF
        elif name == 'r8d':
            return self.regs['r8'] & 0xFFFFFFFF
        elif name == 'r9d':
            return self.regs['r9'] & 0xFFFFFFFF
        if name == 'al':
            return self.regs['rax'] & 0xFF
        elif name == 'bl':
            return self.regs['rbx'] & 0xFF
        elif name == 'cl':
            return self.regs['rcx'] & 0xFF
        elif name == 'dl':
            return self.regs['rdx'] & 0xFF
        elif name == 'r8b':
            return self.regs['r8'] & 0xFF
        elif name == 'r9b':
            return self.regs['r9'] & 0xFF
        return 0
    def set_reg(self, name: str, value: int) -> None:
        if name in self.regs:
            self.regs[name] = value & 0xFFFFFFFFFFFFFFFF
        elif name == 'eax':
            self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'ebx':
            self.regs['rbx'] = (self.regs['rbx'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'ecx':
            self.regs['rcx'] = (self.regs['rcx'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'edx':
            self.regs['rdx'] = (self.regs['rdx'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'edi':
            self.regs['rdi'] = (self.regs['rdi'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'esi':
            self.regs['rsi'] = (self.regs['rsi'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'r8d':
            self.regs['r8'] = (self.regs['r8'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'r9d':
            self.regs['r9'] = (self.regs['r9'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
        elif name == 'al':
            self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFFFFFFFF00) | (value & 0xFF)
        elif name == 'bl':
            self.regs['rbx'] = (self.regs['rbx'] & 0xFFFFFFFFFFFFFF00) | (value & 0xFF)
        elif name == 'cl':
            self.regs['rcx'] = (self.regs['rcx'] & 0xFFFFFFFFFFFFFF00) | (value & 0xFF)
        elif name == 'dl':
            self.regs['rdx'] = (self.regs['rdx'] & 0xFFFFFFFFFFFFFF00) | (value & 0xFF)
        elif name == 'r8b':
            self.regs['r8'] = (self.regs['r8'] & 0xFFFFFFFFFFFFFF00) | (value & 0xFF)
        elif name == 'r9b':
            self.regs['r9'] = (self.regs['r9'] & 0xFFFFFFFFFFFFFF00) | (value & 0xFF)
    def push(self, value: int) -> None:
        self.regs['rsp'] -= 8
        addr = self.regs['rsp']
        self.stack[addr] = value & 0xFFFFFFFFFFFFFFFF
    def pop(self) -> int:
        addr = self.regs['rsp']
        value = self.stack.get(addr, 0)
        self.regs['rsp'] += 8
        if addr in self.stack:
            del self.stack[addr]
        return value
    def update_flags(self, result: int, size: int = 64) -> None:
        mask = (1 << size) - 1 if size < 64 else 0xFFFFFFFFFFFFFFFF
        result_masked = result & mask
        self.flags['ZF'] = 1 if result_masked == 0 else 0
        sign_bit = (size - 1) if size < 64 else 63
        self.flags['SF'] = 1 if (result_masked >> sign_bit) & 1 else 0
        if result < 0:
            self.flags['CF'] = 1
        else:
            self.flags['CF'] = 0
        if 'OF' not in self.flags:
            self.flags['OF'] = 0
    def _get_operand_size(self, operand: Tuple[str, Any]) -> int:
        op_type, op_data = operand
        if op_type == 'reg':
            reg_name = op_data
            if reg_name in ['al', 'bl', 'cl', 'dl', 'r8b', 'r9b']:
                return 8
            elif reg_name in ['ax', 'bx', 'cx', 'dx']:
                return 16
            elif reg_name in ['eax', 'ebx', 'ecx', 'edx', 'edi', 'esi', 'r8d', 'r9d']:
                return 32
            else:
                return 64
        elif op_type == 'mem':
            return 32
        else:
            return 32
    def _sign_extend(self, value: int, from_size: int) -> int:
        if from_size == 8:
            if value & 0x80:
                return value | 0xFFFFFFFFFFFFFF00
            else:
                return value & 0xFF
        elif from_size == 16:
            if value & 0x8000:
                return value | 0xFFFFFFFFFFFF0000
            else:
                return value & 0xFFFF
        elif from_size == 32:
            if value & 0x80000000:
                return value | 0xFFFFFFFF00000000
            else:
                return value & 0xFFFFFFFF
        else:
            return value & 0xFFFFFFFFFFFFFFFF
    def _evaluate_set_condition(self, mnemonic: str) -> bool:
        zf = self.flags.get('ZF', 0)
        sf = self.flags.get('SF', 0)
        of = self.flags.get('OF', 0)
        cf = self.flags.get('CF', 0)
        if mnemonic == 'sete' or mnemonic == 'setz':
            return zf == 1
        elif mnemonic == 'setne' or mnemonic == 'setnz':
            return zf == 0
        elif mnemonic == 'setl' or mnemonic == 'setnge':
            return sf != of
        elif mnemonic == 'setle' or mnemonic == 'setng':
            return (zf == 1) or (sf != of)
        elif mnemonic == 'setg' or mnemonic == 'setnle':
            return (zf == 0) and (sf == of)
        elif mnemonic == 'setge' or mnemonic == 'setnl':
            return sf == of
        elif mnemonic == 'setb' or mnemonic == 'setnae' or mnemonic == 'setc':
            return cf == 1
        elif mnemonic == 'setbe' or mnemonic == 'setna':
            return (cf == 1) or (zf == 1)
        elif mnemonic == 'seta' or mnemonic == 'setnbe':
            return (cf == 0) and (zf == 0)
        elif mnemonic == 'setae' or mnemonic == 'setnb' or mnemonic == 'setnc':
            return cf == 0
        else:
            print(f"Condición set desconocida: {mnemonic}")
            return False
    def parse_operand(self, op: str) -> Tuple[str, Any]:
        op = op.strip()
        if op in self.regs or op in self.REGISTERS_32BIT or op in self.REGISTERS_8BIT:
            return ('reg', op)
        if op.startswith(('0x', '0X')):
            return ('imm', int(op, 16))
        try:
            return ('imm', int(op))
        except ValueError:
            pass
        mem_match = re.match(r'\[([^\]]+)\]', op)
        if mem_match:
            expr = mem_match.group(1)
            expr = expr.replace(' ', '')
            if '+' in expr:
                parts = expr.split('+', 1)
                base_reg = parts[0].strip()
                offset = int(parts[1].strip(), 0) if len(parts) > 1 else 0
            elif '-' in expr:
                parts = expr.split('-', 1)
                base_reg = parts[0].strip()
                offset = -int(parts[1].strip(), 0) if len(parts) > 1 else 0
            else:
                base_reg = expr.strip()
                offset = 0
            return ('mem', (base_reg, offset))
        if op.startswith('.L') or op.endswith(':'):
            return ('label', op.rstrip(':'))
        return ('unknown', op)
    def get_value(self, operand: Tuple[str, Any]) -> int:
        op_type, op_data = operand
        if op_type == 'reg':
            return self.get_reg(op_data)
        elif op_type == 'imm':
            return op_data
        elif op_type == 'mem':
            base_reg, offset = op_data
            if base_reg == 'rbp':
                addr = self.regs['rbp'] + offset
            else:
                addr = self.get_reg(base_reg) + offset
            val = self.stack.get(addr, 0)
            if base_reg == 'rbp' and abs(offset) <= 20:
                print(f"DEBUG: Leyendo {val} (0x{val:x}) de [rbp{offset:+d}] = 0x{addr:x}, rbp=0x{self.regs['rbp']:x}")
            return val
        elif op_type == 'label':
            return self.labels.get(op_data, 0)
        return 0
    def set_value(self, operand: Tuple[str, Any], value: int) -> None:
        op_type, op_data = operand
        if op_type == 'reg':
            self.set_reg(op_data, value)
        elif op_type == 'mem':
            base_reg, offset = op_data
            if base_reg == 'rbp':
                addr = self.regs['rbp'] + offset
            else:
                addr = self.get_reg(base_reg) + offset
            self.stack[addr] = value & 0xFFFFFFFFFFFFFFFF
            if base_reg == 'rbp' and abs(offset) <= 20:
                print(f"DEBUG: Escribiendo {value} (0x{value:x}) en [rbp{offset:+d}] = 0x{addr:x}, rbp=0x{self.regs['rbp']:x}")
    def execute_instruction(self, asm_line: str) -> Union[bool, str, Tuple[str, Any]]:
        asm_line = asm_line.strip()
        if not asm_line or asm_line.startswith(';') or asm_line.endswith(':'):
            return True
        parts = asm_line.split(None, 1)
        if not parts:
            return True
        mnemonic = parts[0].lower()
        operands_str = parts[1] if len(parts) > 1 else ''
        operands = [self.parse_operand(op.strip())
                   for op in operands_str.split(',')] if operands_str else []
        try:
            return self._execute_mnemonic(mnemonic, operands)
        except Exception as e:
            print(f"Error ejecutando {asm_line}: {str(e)}")
            return True
    def _execute_mnemonic(self, mnemonic: str, operands: List[Tuple[str, Any]]) -> Union[bool, str, Tuple[str, Any]]:
        if mnemonic == 'mov':
            if len(operands) == 2:
                src_val = self.get_value(operands[1])
                self.set_value(operands[0], src_val)
            return True
        elif mnemonic == 'lea':
            if len(operands) == 2 and operands[1][0] == 'mem':
                base_reg, offset = operands[1][1]
                addr = self.get_reg(base_reg) + offset
                self.set_value(operands[0], addr)
            return True
        elif mnemonic == 'movsx':
            if len(operands) == 2:
                src_val = self.get_value(operands[1])
                src_size = self._get_operand_size(operands[1])
                extended_val = self._sign_extend(src_val, src_size)
                self.set_value(operands[0], extended_val)
            return True
        elif mnemonic == 'movzx':
            if len(operands) == 2:
                src_val = self.get_value(operands[1])
                src_size = self._get_operand_size(operands[1])
                if src_size == 8:
                    extended_val = src_val & 0xFF
                elif src_size == 16:
                    extended_val = src_val & 0xFFFF
                elif src_size == 32:
                    extended_val = src_val & 0xFFFFFFFF
                else:
                    extended_val = src_val
                self.set_value(operands[0], extended_val)
            return True
        elif mnemonic == 'add':
            if len(operands) == 2:
                dst_val = self.get_value(operands[0])
                src_val = self.get_value(operands[1])
                result = dst_val + src_val
                self.set_value(operands[0], result)
                self.update_flags(result)
                if operands[0][0] == 'mem':
                    base_reg, offset = operands[0][1]
                    if base_reg == 'rbp' and abs(offset) <= 20:
                        print(f"DEBUG: add [rbp{offset:+d}]: {dst_val} + {src_val} = {result}")
            return True
        elif mnemonic == 'sub':
            if len(operands) == 2:
                dst_val = self.get_value(operands[0])
                src_val = self.get_value(operands[1])
                result = dst_val - src_val
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'imul':
            if len(operands) >= 2:
                dst_val = self.get_value(operands[0])
                src_val = self.get_value(operands[1])
                result = dst_val * src_val
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'mul':
            if len(operands) >= 1:
                val = self.get_value(operands[0])
                result = self.regs['rax'] * val
                self.regs['rax'] = result & 0xFFFFFFFFFFFFFFFF
                self.regs['rdx'] = (result >> 64) & 0xFFFFFFFFFFFFFFFF
                self.update_flags(result)
            return True
        elif mnemonic in ['idiv', 'div']:
            if len(operands) >= 1:
                divisor = self.get_value(operands[0])
                if divisor != 0:
                    dividend = self.regs['rax']
                    quotient = dividend // divisor
                    remainder = dividend % divisor
                    self.regs['rax'] = quotient & 0xFFFFFFFFFFFFFFFF
                    self.regs['rdx'] = remainder & 0xFFFFFFFFFFFFFFFF
            return True
        elif mnemonic == 'inc':
            if len(operands) == 1:
                val = self.get_value(operands[0])
                result = val + 1
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'dec':
            if len(operands) == 1:
                val = self.get_value(operands[0])
                result = val - 1
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'neg':
            if len(operands) == 1:
                val = self.get_value(operands[0])
                result = -val
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic in ['and', 'or', 'xor']:
            if len(operands) == 2:
                dst_val = self.get_value(operands[0])
                src_val = self.get_value(operands[1])
                if mnemonic == 'and':
                    result = dst_val & src_val
                elif mnemonic == 'or':
                    result = dst_val | src_val
                else:
                    result = dst_val ^ src_val
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'not':
            if len(operands) == 1:
                val = self.get_value(operands[0])
                result = ~val
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic in ['shl', 'sal']:
            if len(operands) == 2:
                dst_val = self.get_value(operands[0])
                shift = self.get_value(operands[1])
                result = dst_val << shift
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'shr':
            if len(operands) == 2:
                dst_val = self.get_value(operands[0])
                shift = self.get_value(operands[1])
                result = dst_val >> shift
                self.set_value(operands[0], result)
                self.update_flags(result)
            return True
        elif mnemonic == 'cmp':
            if len(operands) == 2:
                val1 = self.get_value(operands[0])
                val2 = self.get_value(operands[1])
                result = val1 - val2
                self.update_flags(result, size=64)
                val1_signed = val1 if val1 < 2**63 else val1 - 2**64
                val2_signed = val2 if val2 < 2**63 else val2 - 2**64
                val1_positive = val1_signed >= 0
                val2_positive = val2_signed >= 0
                result_positive = result >= 0
                if (val1_positive and not val2_positive and not result_positive) or \
                   (not val1_positive and val2_positive and result_positive):
                    self.flags['OF'] = 1
                else:
                    self.flags['OF'] = 0
                print(f"DEBUG: cmp {val1} vs {val2} = {result}, ZF={self.flags['ZF']}, SF={self.flags['SF']}, OF={self.flags['OF']}, CF={self.flags.get('CF', 0)}")
            return True
        elif mnemonic == 'test':
            if len(operands) == 2:
                val1 = self.get_value(operands[0])
                val2 = self.get_value(operands[1])
                result = val1 & val2
                self.update_flags(result)
            return True
        elif mnemonic == 'push':
            if len(operands) == 1:
                val = self.get_value(operands[0])
                self.push(val)
            return True
        elif mnemonic == 'pop':
            if len(operands) == 1:
                val = self.pop()
                self.set_value(operands[0], val)
            return True
        elif mnemonic == 'nop':
            return True
        elif mnemonic == 'leave':
            old_rbp = self.regs['rbp']
            self.regs['rsp'] = self.regs['rbp']
            self.regs['rbp'] = self.pop()
            if self.call_stack:
                if len(self.call_stack) > 0:
                    self.call_stack.pop()
            return True
        elif mnemonic == 'call':
            if operands:
                return ('call', operands[0])
            return True
        elif mnemonic == 'ret':
            return 'ret'
        elif mnemonic.startswith('set'):
            if len(operands) == 1:
                condition_met = self._evaluate_set_condition(mnemonic)
                self.set_value(operands[0], 1 if condition_met else 0)
            return True
        elif mnemonic in ['jmp', 'je', 'jne', 'jl', 'jg', 'jle', 'jge', 'jnz', 'jz']:
            return ('jump', mnemonic, operands[0] if operands else None)
        else:
            print(f"Instrucción no implementada: {mnemonic}")
            return True
    def get_snapshot(self, instruction_data: Dict[str, Any]) -> Dict[str, Any]:
        registers = {}
        all_regs = self.REGISTERS_64BIT + self.REGISTERS_32BIT
        for reg_name in all_regs:
            val = self.get_reg(reg_name)
            registers[reg_name] = {
                'hex': f'0x{val:x}',
                'decimal': val if val < 2**63 else val - 2**64
            }
        stack_list = []
        if self.stack:
            min_addr = min(self.stack.keys())
            max_addr = max(self.stack.keys())
            current_rsp = self.regs['rsp']
            start_addr = min(min_addr, current_rsp)
            end_addr = max(max_addr, current_rsp)
            for addr in range(start_addr, end_addr + 8, 8):
                val = self.stack.get(addr, 0)
                decimal_val = val if val < 2**63 else val - 2**64
                var_label = None
                if self.call_stack:
                    active_frame = self.call_stack[-1]
                    rbp = active_frame.get('rbp', 0)
                    stack_frame_info = active_frame.get('stackFrame', [])
                    for var_info in stack_frame_info:
                        var_offset = var_info.get('offset', 0)
                        var_addr = rbp - var_offset
                        if var_addr == addr:
                            var_label = var_info.get('varName', '')
                            break
                stack_list.append({
                    'address': f'0x{addr:x}',
                    'addressDecimal': addr,
                    'value': f'0x{val:x}',
                    'decimal': decimal_val,
                    'variable': var_label
                })
        else:
            rsp = self.regs['rsp']
            stack_list.append({
                'address': f'0x{rsp:x}',
                'addressDecimal': rsp,
                'value': '0x0',
                'decimal': 0,
                'variable': None
            })
        call_stack_list = []
        for i, frame in enumerate(self.call_stack):
            function_name = frame.get('function', 'unknown')
            rbp = frame.get('rbp', 0)
            stack_frame_info = frame.get('stackFrame', [])
            is_active = (i == len(self.call_stack) - 1)
            frame_vars = {}
            if not stack_frame_info:
                print(f"WARNING: Frame {function_name} has no stack_frame_info!")
            for var_info in stack_frame_info:
                var_name = var_info.get('varName', '')
                if not var_name:
                    continue
                offset = var_info.get('offset', 0)
                var_type = var_info.get('type', 'int')
                current_rbp = self.regs['rbp']
                rbp_to_use = current_rbp
                var_addr = rbp_to_use - offset
                if var_type == 'long':
                    var_value = self.stack.get(var_addr, 0)
                    if var_value >= 2**63:
                        var_value_signed = var_value - 2**64
                    else:
                        var_value_signed = var_value
                else:
                    var_value_raw = self.stack.get(var_addr, 0)
                    var_value = var_value_raw & 0xFFFFFFFF
                    if var_value >= 2**31:
                        var_value_signed = var_value - 2**32
                    else:
                        var_value_signed = var_value
                if abs(offset) <= 20:
                    print(f"DEBUG: Variable {var_name}: addr=0x{var_addr:x}, valor={var_value_signed}, en_stack={var_addr in self.stack}, stack_size={len(self.stack)}")
                    if var_addr in self.stack:
                        print(f"  Stack[{var_addr:x}] = {self.stack[var_addr]} (raw)")
                frame_vars[var_name] = {
                    'value': var_value_signed,
                    'hex': f'0x{var_value:x}',
                    'type': var_type,
                    'address': f'0x{var_addr:x}',
                    'addressDecimal': var_addr,
                    'offset': offset,
                    'initialized': var_addr in self.stack
                }
            call_stack_list.append({
                'function': function_name,
                'rbp': f'0x{rbp:x}',
                'rbpDecimal': rbp,
                'variables': frame_vars,
                'isActive': is_active
            })
        return {
            'instruction': instruction_data,
            'registers': registers,
            'stack': stack_list,
            'callStack': call_stack_list,
            'flags': {
                'ZF': self.flags.get('ZF', 0),
                'SF': self.flags.get('SF', 0),
                'CF': self.flags.get('CF', 0),
                'OF': self.flags.get('OF', 0)
            }
        }


def emulate_from_debug(debug_data: Dict[str, Any], max_steps: int = 1000) -> List[Dict[str, Any]]:
    emulator = X86Emulator()
    instructions = debug_data.get('instructions', [])
    stack_frames_info = debug_data.get('stackFrame', [])
    snapshots = []

    print(f"=== DEBUG EMULATOR ===")
    print(f"Debug data keys: {list(debug_data.keys())}")
    print(f"Instructions count: {len(instructions)}")
    print(f"StackFrame count: {len(stack_frames_info)}")
    print(f"StackFrame type: {type(stack_frames_info)}")
    logger.info(f"DEBUG:'")
    print(f"DEBUG: Estructura completa de debug_data:")
    for key, value in debug_data.items():
        if isinstance(value, list):
            print(f"  {key}: list con {len(value)} elementos")
            if value and isinstance(value[0], dict):
                print(f"    Primer elemento keys: {list(value[0].keys())}")
        elif isinstance(value, dict):
            print(f"  {key}: dict con keys: {list(value.keys())}")
        else:
            print(f"  {key}: {type(value)} = {str(value)[:100]}")
    if stack_frames_info:
        print(f"First stackFrame item: {stack_frames_info[0]}")
        print(f"StackFrame keys: {stack_frames_info[0].keys() if isinstance(stack_frames_info[0], dict) else 'Not a dict'}")
    else:
        print("WARNING: stackFrame is EMPTY!")
        print(f"Debug data sample: {str(debug_data)[:1000]}")
    print(f"=======================")
    current_function = None
    function_start_pc = {}
    print(f"DEBUG: Mapeando labels de {len(instructions)} instrucciones...")
    print(f"DEBUG: Tipo de instructions: {type(instructions)}")
    if instructions:
        print(f"DEBUG: Tipo del primer elemento: {type(instructions[0])}")
        print(f"DEBUG: Keys del primer elemento: {list(instructions[0].keys()) if isinstance(instructions[0], dict) else 'No es dict'}")
    print(f"DEBUG: Primeras 5 instrucciones para verificar formato:")
    for i in range(min(5, len(instructions))):
        inst = instructions[i]
        if isinstance(inst, dict):
            asm = inst.get('assembly', '')
            print(f"  [{i}] assembly='{asm[:100]}...' (tipo={type(asm)})")
        else:
            print(f"  [{i}] NO ES DICT: {type(inst)} = {inst}")
    for i, inst in enumerate(instructions):
        asm_raw = inst.get('assembly', '')
        if not asm_raw:
            continue
        asm = str(asm_raw).strip()
        lines = asm.split('\n')
        first_line = lines[0].strip()
        if ':' in first_line:
            print(f"DEBUG: Línea {i} primera línea: '{first_line}' (contiene ':')")
        if first_line.endswith(':'):
            potential_label = first_line.rstrip(':').strip()
            if potential_label and not potential_label.startswith(';'):
                emulator.labels[potential_label] = i
                print(f"DEBUG: Label '{potential_label}' mapeado a índice {i}")
                if not potential_label.startswith('.L') and \
                   not potential_label.startswith('while_') and \
                   not potential_label.startswith('if_') and \
                   not potential_label.startswith('else_') and \
                   not potential_label.startswith('endif_') and \
                   not potential_label.startswith('for_') and \
                   not potential_label.startswith('end_'):
                    current_function = potential_label
                    function_start_pc[potential_label] = i
                    emulator.function_frames[potential_label] = []
                    print(f"DEBUG: Función '{potential_label}' detectada en índice {i}")
    print(f"DEBUG:  Total labels mapeados: {len(emulator.labels)}")
    if emulator.labels:
        print(f"DEBUG: Labels encontrados: {list(emulator.labels.keys())}")
    else:
        print(f"DEBUG:  WARNING - NO SE ENCONTRARON LABELS!")
    function_vars: Dict[str, List[Dict[str, Any]]] = {}
    for func_name in function_start_pc.keys():
        function_vars[func_name] = []
    if 'main' not in function_vars:
        function_vars['main'] = []
    for func_name in function_vars.keys():
        function_vars[func_name] = stack_frames_info.copy() if stack_frames_info else []
    print(f"Stack frames info count: {len(stack_frames_info)}")
    print(f"Functions detected: {list(function_vars.keys())}")
    if stack_frames_info:
        print(f"First variable: {stack_frames_info[0] if stack_frames_info else 'None'}")
    emulator.function_frames = function_vars
    main_stack_frame = emulator.function_frames.get('main', [])
    if not main_stack_frame and stack_frames_info:
        main_stack_frame = stack_frames_info.copy()
        emulator.function_frames['main'] = main_stack_frame
    print(f"DEBUG: Updated frame rbp to: 0x{emulator.regs['rbp']:x}")
    main_frame = {
        'function': 'main',
        'rbp': emulator.regs['rbp'],
        'return_pc': None,
        'stackFrame': main_stack_frame
    }
    emulator.call_stack.append(main_frame)
    print(f"Main frame variables count: {len(main_stack_frame)}")
    if instructions:
        first_inst = instructions[0]
        snapshots.append(emulator.get_snapshot({
            'id': -1,
            'assembly': 'INIT',
            'sourceLine': first_inst.get('sourceLine', 0),
            'line': first_inst.get('line', 0)
        }))
    pc = 0
    step_count = 0
    print(f"DEBUG: Iniciando ejecución con {len(instructions)} instrucciones, max_steps={max_steps}")
    print(f"DEBUG: Labels mapeados: {list(emulator.labels.keys())}")
    while pc is not None and pc < len(instructions) and step_count < max_steps:
        inst = instructions[pc]
        asm = inst.get('assembly', '').strip()
        first_line = asm.split('\n')[0].strip()
        if first_line.endswith(':'):
            label = first_line.rstrip(':')
            print(f"DEBUG: Procesando label '{label}' en PC={pc}")
            if label in function_start_pc and label != 'main':
                if emulator.call_stack:
                    frame_found = False
                    for frame in emulator.call_stack:
                        if frame['function'] == label:
                            frame_found = True
                            break
                    if not frame_found:
                        new_frame = {
                            'function': label,
                            'rbp': emulator.regs['rbp'],
                            'return_pc': None,
                            'stackFrame': emulator.function_frames.get(label, [])
                        }
                        emulator.call_stack.append(new_frame)
            pc += 1
            print(f"DEBUG: Saltando label, nuevo PC={pc}")
            continue
        if step_count < 10 or 'jmp' in first_line.lower() or 'jl' in first_line.lower() or 'jge' in first_line.lower():
            print(f"DEBUG: Ejecutando PC={pc}: '{first_line}'")
        result = emulator.execute_instruction(asm)
        if emulator.call_stack:
            emulator.call_stack[-1]['rbp'] = emulator.regs['rbp']
        if 'rbp' in first_line.lower() or 'jmp' in first_line.lower() or 'jl' in first_line.lower() or 'jge' in first_line.lower():
            print(f"DEBUG: Antes snapshot - RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}, RSP=0x{emulator.regs['rsp']:x}")
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]}")
        snapshots.append(emulator.get_snapshot({
            'id': inst.get('id', pc),
            'assembly': asm,
            'sourceLine': inst.get('sourceLine', 0),
            'line': inst.get('line', inst.get('sourceLine', 0))
        }))
        step_count += 1
        if isinstance(result, tuple) and result[0] == 'call':
            pc = _handle_call(emulator, result[1], instructions, pc, debug_data)
            continue
        if isinstance(result, tuple) and result[0] == 'jump':
            old_pc = pc
            print(f"DEBUG: ANTES salto - PC={pc}, RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}")
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]} (antes salto)")
            pc = _handle_jump(emulator, result[1], result[2], instructions, pc)
            if emulator.call_stack:
                emulator.call_stack[-1]['rbp'] = emulator.regs['rbp']
            print(f"DEBUG: DESPUÉS salto - PC={pc}, RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}")
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]} (después salto)")
            if pc != old_pc + 1:
                print(f"DEBUG: Salto ejecutado: PC {old_pc} -> {pc} ({result[1]})")
                if pc < len(instructions):
                    next_inst = instructions[pc].get('assembly', '').strip().split('\n')[0]
                    print(f"DEBUG: Próxima instrucción después del salto (PC={pc}): '{next_inst}'")
            continue
        if result == 'ret':
            if emulator.call_stack:
                emulator.call_stack.pop()
            pc = _handle_ret(emulator, instructions, pc)
            if pc is None:
                break
            continue
        pc += 1
    if pc is None:
        print(f"DEBUG: Loop terminó porque PC se volvió None")
    elif step_count >= max_steps:
        print(f"DEBUG: WARNING - Loop terminó por límite de pasos ({max_steps})")
    elif pc >= len(instructions):
        print(f"DEBUG: Loop terminó porque PC ({pc}) >= len(instructions) ({len(instructions)})")
    else:
        print(f"DEBUG: Loop terminó por otra razón: PC={pc}, step_count={step_count}, max_steps={max_steps}")
    for i, snapshot in enumerate(snapshots):
        snapshot['step'] = i
    print(f"Emulated {len(snapshots)} execution snapshots")
    print(f"Execution snapshots generated: {len(snapshots)} steps")
    return snapshots
def _handle_call(emulator: X86Emulator, target_operand: Any,
                 instructions: List[Dict], pc: int, debug_data: Dict[str, Any] = None) -> int:
    if isinstance(target_operand, tuple) and target_operand[0] == 'label':
        target_label = target_operand[1]
    else:
        target_label = str(target_operand)
    emulator.push(pc + 1)
    old_rbp = emulator.regs['rbp']
    target_pc = None
    if target_label in emulator.labels:
        target_pc = emulator.labels[target_label]
    else:
        for i, inst_check in enumerate(instructions):
            asm_check = inst_check.get('assembly', '').strip().rstrip(':')
            if asm_check == target_label or asm_check == target_label + ':':
                target_pc = i
                break
    if target_pc is None:
        return pc + 1
    new_frame = {
        'function': target_label,
        'rbp': emulator.regs['rbp'],
        'return_pc': pc + 1,
        'stackFrame': emulator.function_frames.get(target_label, [])
    }
    emulator.call_stack.append(new_frame)
    return target_pc


def _handle_jump(emulator: X86Emulator, jump_type: str, target_operand: Any,
                 instructions: List[Dict], pc: int) -> int:
    should_jump = False
    zf = emulator.flags.get('ZF', 0)
    sf = emulator.flags.get('SF', 0)
    of = emulator.flags.get('OF', 0)
    cf = emulator.flags.get('CF', 0)
    if jump_type == 'jmp':
        should_jump = True
    elif jump_type in ['je', 'jz']:
        should_jump = (zf == 1)
    elif jump_type in ['jne', 'jnz']:
        should_jump = (zf == 0)
    elif jump_type == 'jl':
        should_jump = (sf != of)
    elif jump_type == 'jle':
        should_jump = (zf == 1) or (sf != of)
    elif jump_type == 'jg':
        should_jump = (zf == 0) and (sf == of)
    elif jump_type == 'jge':
        should_jump = (sf == of)
    elif jump_type == 'jb' or jump_type == 'jnae' or jump_type == 'jc':
        should_jump = (cf == 1)
    elif jump_type == 'jbe' or jump_type == 'jna':
        should_jump = (cf == 1) or (zf == 1)
    elif jump_type == 'ja' or jump_type == 'jnbe':
        should_jump = (cf == 0) and (zf == 0)
    elif jump_type == 'jae' or jump_type == 'jnb' or jump_type == 'jnc':
        should_jump = (cf == 0)
    if target_operand:
        target_str = str(target_operand[1]) if isinstance(target_operand, tuple) else str(target_operand)
        print(f"DEBUG: {jump_type} -> {target_str}, should_jump={should_jump}, ZF={zf}, SF={sf}, OF={of}, CF={cf}")
    if not should_jump or not target_operand:
        return pc + 1
    if isinstance(target_operand, tuple):
        if target_operand[0] == 'label':
            target_label = target_operand[1]
        elif len(target_operand) > 1:
            target_label = str(target_operand[1])
        else:
            target_label = str(target_operand[0]) if target_operand else None
    else:
        target_label = str(target_operand)
    if target_label:
        target_label = target_label.strip().rstrip(':')
    print(f"DEBUG: Buscando label '{target_label}' en {len(emulator.labels)} labels mapeados")
    if target_label and target_label in emulator.labels:
        target_pc = emulator.labels[target_label]
        print(f"DEBUG: Label '{target_label}' encontrado en índice {target_pc}")
        if target_pc is not None and isinstance(target_pc, int) and 0 <= target_pc < len(instructions):
            next_inst = instructions[target_pc].get('assembly', '').strip()
            print(f"DEBUG: Instrucción en índice {target_pc}: '{next_inst}'")
            if next_inst.endswith(':'):
                print(f"DEBUG: Es un label, la siguiente instrucción será ejecutada")
            return target_pc
        else:
            print(f"DEBUG: ERROR - Índice {target_pc} inválido (tipo={type(target_pc)}, len={len(instructions)})")
    print(f"DEBUG: Buscando label '{target_label}' manualmente en instrucciones...")
    for i, inst_check in enumerate(instructions):
        asm_check = inst_check.get('assembly', '').strip()
        asm_label = asm_check.rstrip(':').strip()
        if asm_label == target_label or asm_check == target_label + ':' or asm_check == target_label:
            print(f"DEBUG: Label '{target_label}' encontrado manualmente en índice {i}: '{asm_check}'")
            emulator.labels[target_label] = i
            return i
    print(f"DEBUG: WARNING - Label '{target_label}' NO encontrado en {len(emulator.labels)} labels")
    print(f"DEBUG: Labels disponibles: {list(emulator.labels.keys())[:20]}")
    next_pc = pc + 1 if pc is not None else 0
    print(f"DEBUG: Continuando con PC+1 ({next_pc})")
    return next_pc


def _handle_ret(emulator: X86Emulator, instructions: List[Dict], pc: int) -> Optional[int]:
    print(f"DEBUG: ret - RSP=0x{emulator.regs['rsp']:x}, RBP=0x{emulator.regs['rbp']:x}")
    print(f"DEBUG: ret - Stack size: {len(emulator.stack)}")
    if emulator.regs['rsp'] < X86Emulator.INITIAL_STACK_POINTER:
        try:
            return_addr = emulator.pop()
            print(f"DEBUG: ret - Popped return address: 0x{return_addr:x} (PC={return_addr})")
            if isinstance(return_addr, int) and 0 <= return_addr < len(instructions):
                return return_addr
        except (KeyError, IndexError):
            print(f"DEBUG: ret - Stack vacío o error al hacer pop, terminando ejecución")
            pass
    print(f"DEBUG: ret - Finalizando ejecución")
    print(f"DEBUG: ret - RBP final: 0x{emulator.regs['rbp']:x}, RSP final: 0x{emulator.regs['rsp']:x}")
    return None

