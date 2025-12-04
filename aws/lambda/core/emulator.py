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
        # Registros XMM para floats (guardamos como int, interpretamos como float cuando sea necesario)
        self.xmm_regs: Dict[str, float] = {
            reg: 0.0 for reg in self.REGISTERS_XMM
        }
        self.flags: Dict[str, int] = {'ZF': 0, 'SF': 0, 'CF': 0, 'OF': 0}
        self.stack: Dict[int, int] = {}
        self.labels: Dict[str, int] = {}
        self.call_stack: List[Dict[str, Any]] = []
        self.function_frames: Dict[str, List[Dict[str, Any]]] = {}
        # Rastreo de valores de variables por nombre
        self.variable_values: Dict[str, int] = {}
        # Rastreo de valores en el stack antes de que se eliminen (para pop)
        self.stack_before_pop: Dict[int, int] = {}
        # Mapa del stack frame: dirección -> información (variable local o temporal)
        self.stack_frame_map: Dict[int, Dict[str, Any]] = {}
        # Contador de step para rastrear valores temporales
        self.current_step: int = 0
        # Valores de registros antes de ejecutar una instrucción (para descripciones)
        self.registers_before_instruction: Dict[str, int] = {}
    
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
        if name in self.REGISTERS_XMM:
            # Para XMM, convertir int a float
            import struct
            self.xmm_regs[name] = struct.unpack('f', struct.pack('I', value & 0xFFFFFFFF))[0]
        elif name in self.regs:
            self.regs[name] = value & 0xFFFFFFFFFFFFFFFF
            # Cuando se actualiza un registro de 64 bits, también actualizar sus alias de 32 bits
            # Por ejemplo: rbx -> ebx, rax -> eax, etc.
            if name == 'rbx':
                # No hay un registro ebx separado, se accede como los 32 bits bajos de rbx
                pass
            elif name == 'rax':
                pass
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
        # Guardar el valor antes de eliminarlo del stack
        self.stack_before_pop[addr] = value
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
        # Quitar el % si está presente (sintaxis AT&T)
        if op.startswith('%'):
            reg_name = op[1:]
            if reg_name in self.regs or reg_name in self.REGISTERS_32BIT or reg_name in self.REGISTERS_8BIT or reg_name in self.REGISTERS_XMM:
                return ('reg', reg_name)
        # También verificar sin % por si acaso
        if op in self.regs or op in self.REGISTERS_32BIT or op in self.REGISTERS_8BIT or op in self.REGISTERS_XMM:
            return ('reg', op)
        if op.startswith('$'):
            # Inmediato con $ (sintaxis AT&T)
            op = op[1:]
        if op.startswith(('0x', '0X')):
            return ('imm', int(op, 16))
        try:
            return ('imm', int(op))
        except ValueError:
            pass
        
        # Sintaxis AT&T: offset(%reg) o (%reg)
        att_mem_match = re.match(r'(-?\d+)\(%(\w+)\)', op)
        if att_mem_match:
            offset = int(att_mem_match.group(1))
            base_reg = att_mem_match.group(2)
            return ('mem', (base_reg, offset))
        
        att_mem_no_offset = re.match(r'\(%(\w+)\)', op)
        if att_mem_no_offset:
            base_reg = att_mem_no_offset.group(1)
            return ('mem', (base_reg, 0))
        
        # Sintaxis Intel: [reg+offset] o [reg]
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
        if op.startswith('.L') or op.endswith(':') or op.startswith('while_') or op.startswith('.end_'):
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
        mnemonic_full = parts[0].lower()
        
        # Quitar sufijos de tamaño (l=32, q=64, b=8, w=16) para obtener el mnemonic base
        # PERO: Algunos mnemonics tienen sufijos que son parte del nombre, no tamaños
        if mnemonic_full.startswith('set') or mnemonic_full.startswith('j') or mnemonic_full.startswith('cmov'):
            # Para SET, JMP, CMOV el sufijo es parte del nombre, no un tamaño
            mnemonic = mnemonic_full
        elif mnemonic_full in ['movzbq', 'movzbl', 'movzbw', 'movzwl', 'movzwq']:
            # movzbq -> movzx, movzbl -> movzx, etc. (move with zero extension)
            mnemonic = 'movzx'
        elif mnemonic_full in ['movsbl', 'movsbw', 'movsbq', 'movswl', 'movswq', 'movslq']:
            # movsbl -> movsx, etc. (move with sign extension)  
            mnemonic = 'movsx'
        elif mnemonic_full in ['cltq', 'cltd', 'cqto']:
            # Instrucciones de conversión de signo - NO quitar sufijos
            mnemonic = mnemonic_full
        elif mnemonic_full.endswith(('l', 'q', 'b', 'w')):
            mnemonic = mnemonic_full[:-1]
        else:
            mnemonic = mnemonic_full
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
                # En sintaxis AT&T: mov src, dst → dst = src
                src_val = self.get_value(operands[0])  # FUENTE es operands[0]
                print(f"DEBUG MOV: operands={operands}, src_val={src_val}, dst={operands[1]}")
                self.set_value(operands[1], src_val)  # DESTINO es operands[1]
                # Verificar que se guardó correctamente
                if operands[1][0] == 'reg':
                    reg_name = operands[1][1]
                    new_val = self.get_reg(reg_name)
                    print(f"DEBUG MOV: Después de guardar, %{reg_name} = {new_val}")
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
                # En sintaxis AT&T: add src, dst → dst = dst + src
                print(f"DEBUG ADD: operands={operands}")
                src_val = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                print(f"DEBUG ADD: src_val={src_val}, dst_val={dst_val}, src_type={operands[0][0]}, dst_type={operands[1][0]}")
                result = dst_val + src_val
                print(f"DEBUG ADD: result={result}, guardando en operands[1]={operands[1]}")
                self.set_value(operands[1], result)  # Guardar en destino
                self.update_flags(result)
                if operands[1][0] == 'mem':
                    base_reg, offset = operands[1][1]
                    if base_reg == 'rbp' and abs(offset) <= 20:
                        print(f"DEBUG: add [rbp{offset:+d}]: {dst_val} + {src_val} = {result}")
            return True
        elif mnemonic == 'sub':
            if len(operands) == 2:
                # En sintaxis AT&T: sub src, dst → dst = dst - src
                src_val = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                result = dst_val - src_val
                self.set_value(operands[1], result)  # Guardar en destino
                self.update_flags(result)
            return True
        elif mnemonic == 'imul':
            if len(operands) >= 2:
                # En sintaxis AT&T: imul src, dst → dst = dst * src
                src_val = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                result = dst_val * src_val
                self.set_value(operands[1], result)  # Guardar en destino
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
                # En sintaxis AT&T: op src, dst → dst = dst op src
                src_val = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                if mnemonic == 'and':
                    result = dst_val & src_val
                elif mnemonic == 'or':
                    result = dst_val | src_val
                else:
                    result = dst_val ^ src_val
                self.set_value(operands[1], result)  # Guardar en destino
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
                # En sintaxis AT&T: shl shift, dst → dst = dst << shift
                shift = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                result = dst_val << shift
                self.set_value(operands[1], result)  # Guardar en destino
                self.update_flags(result)
            return True
        elif mnemonic == 'shr':
            if len(operands) == 2:
                # En sintaxis AT&T: shr shift, dst → dst = dst >> shift
                shift = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                result = dst_val >> shift
                self.set_value(operands[1], result)  # Guardar en destino
                self.update_flags(result)
            return True
        elif mnemonic == 'cmp':
            if len(operands) == 2:
                # En sintaxis AT&T: cmp src, dst hace dst - src
                print(f"DEBUG CMP OPERANDS: op0={operands[0]}, op1={operands[1]}")
                print(f"DEBUG CMP REGISTERS BEFORE: eax={self.get_reg('eax')}, ebx={self.get_reg('ebx')}, rax={self.get_reg('rax')}, rbx={self.get_reg('rbx')}")
                src_val = self.get_value(operands[0])
                dst_val = self.get_value(operands[1])
                print(f"DEBUG CMP VALUES: src_val={src_val}, dst_val={dst_val}")
                
                # Para cmpl, solo usar los 32 bits inferiores
                if len(operands) >= 2 and operands[1][0] == 'reg' and operands[1][1].startswith('e'):
                    src_val = src_val & 0xFFFFFFFF
                    dst_val = dst_val & 0xFFFFFFFF
                    result = dst_val - src_val
                    # Manejar overflow de 32 bits
                    if result < -(2**31):
                        result += 2**32
                    elif result >= 2**31:
                        result -= 2**32
                    self.update_flags(result, size=32)
                else:
                    result = dst_val - src_val
                    self.update_flags(result, size=64)
                
                dst_signed = dst_val if dst_val < 2**63 else dst_val - 2**64
                src_signed = src_val if src_val < 2**63 else src_val - 2**64
                dst_positive = dst_signed >= 0
                src_positive = src_signed >= 0
                result_positive = result >= 0
                if (dst_positive and not src_positive and not result_positive) or \
                   (not dst_positive and src_positive and result_positive):
                    self.flags['OF'] = 1
                else:
                    self.flags['OF'] = 0
                print(f"DEBUG: cmp {dst_val} vs {src_val} = {result}, ZF={self.flags['ZF']}, SF={self.flags['SF']}, OF={self.flags['OF']}, CF={self.flags.get('CF', 0)}")
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
                # Guardar el valor antes de que se elimine del stack
                addr = self.regs['rsp']
                if addr in self.stack:
                    self.stack_before_pop[addr] = self.stack[addr]
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
        elif mnemonic == 'movss':
            # Move Scalar Single-precision Float
            if len(operands) == 2:
                src_val = self.get_value(operands[0])
                self.set_value(operands[1], src_val)
            return True
        elif mnemonic == 'addss':
            # Add Scalar Single-precision Float
            if len(operands) == 2:
                import struct
                # Obtener valores como floats
                src_int = self.get_value(operands[0])
                dst_int = self.get_value(operands[1])
                src_float = struct.unpack('f', struct.pack('I', src_int & 0xFFFFFFFF))[0]
                dst_float = struct.unpack('f', struct.pack('I', dst_int & 0xFFFFFFFF))[0]
                result_float = dst_float + src_float
                # Convertir resultado a int
                result_int = struct.unpack('I', struct.pack('f', result_float))[0]
                self.set_value(operands[1], result_int)
            return True
        elif mnemonic == 'subss':
            # Subtract Scalar Single-precision Float
            if len(operands) == 2:
                import struct
                src_int = self.get_value(operands[0])
                dst_int = self.get_value(operands[1])
                src_float = struct.unpack('f', struct.pack('I', src_int & 0xFFFFFFFF))[0]
                dst_float = struct.unpack('f', struct.pack('I', dst_int & 0xFFFFFFFF))[0]
                result_float = dst_float - src_float
                result_int = struct.unpack('I', struct.pack('f', result_float))[0]
                self.set_value(operands[1], result_int)
            return True
        elif mnemonic == 'mulss':
            # Multiply Scalar Single-precision Float
            if len(operands) == 2:
                import struct
                src_int = self.get_value(operands[0])
                dst_int = self.get_value(operands[1])
                src_float = struct.unpack('f', struct.pack('I', src_int & 0xFFFFFFFF))[0]
                dst_float = struct.unpack('f', struct.pack('I', dst_int & 0xFFFFFFFF))[0]
                result_float = dst_float * src_float
                result_int = struct.unpack('I', struct.pack('f', result_float))[0]
                self.set_value(operands[1], result_int)
            return True
        elif mnemonic == 'divss':
            # Divide Scalar Single-precision Float
            if len(operands) == 2:
                import struct
                src_int = self.get_value(operands[0])
                dst_int = self.get_value(operands[1])
                src_float = struct.unpack('f', struct.pack('I', src_int & 0xFFFFFFFF))[0]
                dst_float = struct.unpack('f', struct.pack('I', dst_int & 0xFFFFFFFF))[0]
                if src_float != 0.0:
                    result_float = dst_float / src_float
                    result_int = struct.unpack('I', struct.pack('f', result_float))[0]
                    self.set_value(operands[1], result_int)
            return True
        elif mnemonic == 'cltq':
            # Convert Long To Quad - extiende eax (32 bits) a rax (64 bits) con signo
            eax_value = self.regs['rax'] & 0xFFFFFFFF
            if eax_value >= 2**31:
                # Extender signo negativo
                rax_value = eax_value | 0xFFFFFFFF00000000
            else:
                # Extender signo positivo (ceros)
                rax_value = eax_value
            self.regs['rax'] = rax_value & 0xFFFFFFFFFFFFFFFF
            return True
        elif mnemonic in ['jmp', 'je', 'jne', 'jl', 'jg', 'jle', 'jge', 'jnz', 'jz']:
            return ('jump', mnemonic, operands[0] if operands else None)
        else:
            print(f"Instrucción no implementada: {mnemonic}")
            return True
    def _update_stack_frame_map(self, addr: int, entry_type: str, **kwargs) -> None:
        """
        Actualiza el mapa del stack frame con información sobre una dirección.
        entry_type puede ser: 'local_variable', 'temporary', 'reserved'
        """
        if entry_type == 'local_variable':
            self.stack_frame_map[addr] = {
                'type': 'local_variable',
                'name': kwargs.get('name', ''),
                'offset': kwargs.get('offset', 0),
                'value': kwargs.get('value', 0),
                'var_type': kwargs.get('var_type', 'int'),
                'updated_by': kwargs.get('instruction', ''),
                'step': self.current_step
            }
        elif entry_type == 'temporary':
            self.stack_frame_map[addr] = {
                'type': 'temporary',
                'value': kwargs.get('value', 0),
                'source': kwargs.get('source', ''),
                'step': kwargs.get('step', self.current_step),
                'status': 'active'
            }
        elif entry_type == 'reserved':
            self.stack_frame_map[addr] = {
                'type': 'reserved',
                'size': kwargs.get('size', 0),
                'step': self.current_step
            }
    
    def _remove_temporary_from_map(self, addr: int) -> None:
        """Elimina un valor temporal del mapa cuando se hace pop"""
        if addr in self.stack_frame_map:
            entry = self.stack_frame_map[addr]
            if entry.get('type') == 'temporary':
                entry['status'] = 'removed'
                entry['removed_at_step'] = self.current_step
    
    def _cleanup_stack_frame(self) -> None:
        """
        Limpia el stack frame después de leave.
        Elimina todas las variables locales, pero mantiene el return address.
        """
        print(f"DEBUG leave: Limpiando stack_frame_map. Tamaño antes: {len(self.stack_frame_map)}")
        print(f"DEBUG leave: Contenido antes: {list(self.stack_frame_map.keys())}")
        
        # Eliminar todas las variables locales del stack_frame_map
        addrs_to_remove = []
        for addr, entry in self.stack_frame_map.items():
            entry_type = entry.get('type', '')
            if entry_type == 'local_variable':
                addrs_to_remove.append(addr)
                print(f"DEBUG leave: Marcando para eliminar variable local '{entry.get('name', '')}' en addr=0x{addr:x}")
        
        for addr in addrs_to_remove:
            if addr in self.stack_frame_map:
                del self.stack_frame_map[addr]
                print(f"DEBUG leave: Eliminando variable local de addr=0x{addr:x}")
        
        # También limpiar temporales que ya no son relevantes
        temp_addrs_to_remove = []
        for addr, entry in self.stack_frame_map.items():
            entry_type = entry.get('type', '')
            if entry_type == 'temporary':
                temp_addrs_to_remove.append(addr)
                print(f"DEBUG leave: Marcando para eliminar temporal en addr=0x{addr:x}")
        
        for addr in temp_addrs_to_remove:
            if addr in self.stack_frame_map:
                del self.stack_frame_map[addr]
                print(f"DEBUG leave: Eliminando temporal de addr=0x{addr:x}")
        
        print(f"DEBUG leave: Tamaño después: {len(self.stack_frame_map)}")
        print(f"DEBUG leave: Contenido después: {list(self.stack_frame_map.keys())}")
    
    def _analyze_instruction_and_update_variables(self, instruction_data: Dict[str, Any], 
                                                   stack_frame_info: List[Dict[str, Any]]) -> None:
        """
        Analiza una instrucción assembly y actualiza directamente los valores de las variables
        basándose en lo que hace la instrucción. También actualiza el stack_frame_map.
        """
        asm = instruction_data.get('assembly', '').strip()
        if not asm:
            return
        
        first_line = asm.split('\n')[0].strip()
        inst_var_name = instruction_data.get('varName', '')
        
        # Detectar leave y limpiar el stack frame
        if first_line.strip() == 'leave':
            print(f"DEBUG leave: Detectado leave, limpiando stack frame")
            self._cleanup_stack_frame()
            return
        
        # Crear mapa de offset -> variable
        # NOTA: Los offsets en stackFrame son positivos (4, 8, 12) pero en assembly son negativos (-4, -8, -12)
        offset_to_var = {}
        for var_info in stack_frame_info:
            var_name = var_info.get('varName', '')
            if var_name:
                offset_positive = var_info.get('offset', 0)
                # Mapear tanto el offset positivo como el negativo
                offset_to_var[offset_positive] = var_info
                offset_to_var[-offset_positive] = var_info
        
        # Analizar subq $N, %rsp (reservar espacio para variables locales)
        subq_rsp_match = re.match(r'subq\s+\$(\d+),\s*%rsp', first_line)
        if subq_rsp_match:
            size = int(subq_rsp_match.group(1))
            # Marcar el espacio reservado en el stack_frame_map
            rsp_after = self.regs['rsp']
            for i in range(0, size, 8):
                addr = rsp_after + i
                if addr not in self.stack_frame_map:
                    self._update_stack_frame_map(addr, 'reserved', size=8)
            return
        
        # Analizar cltq (Convert Long to Quad - extiende eax a rax)
        cltq_match = re.match(r'cltq', first_line)
        if cltq_match:
            # cltq extiende el signo de eax (32 bits) a rax (64 bits)
            eax_value = self.regs['rax'] & 0xFFFFFFFF
            if eax_value >= 2**31:
                # Extender signo negativo
                rax_value = eax_value | 0xFFFFFFFF00000000
            else:
                # Extender signo positivo (ceros)
                rax_value = eax_value
            self.regs['rax'] = rax_value & 0xFFFFFFFFFFFFFFFF
            # Si hay varName, actualizar esa variable con el valor extendido
            if inst_var_name:
                rax_value_signed = rax_value if rax_value < 2**63 else (rax_value - 2**64)
                self.variable_values[inst_var_name] = rax_value_signed
            return
        
        # Analizar movl $inm, %eax (asignación de constante)
        mov_imm_match = re.match(r'movl\s+\$(\d+),\s*%eax', first_line)
        if mov_imm_match:
            value = int(mov_imm_match.group(1))
            # Si hay varName, actualizar esa variable (crearla si no existe)
            if inst_var_name:
                self.variable_values[inst_var_name] = value
            # También actualizar eax
            self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
            return
        
        # Analizar movq %rax, offset(%rbp) (guardar variable long)
        movq_store_match = re.match(r'movq\s+%rax,\s*(-?\d+)\(%rbp\)', first_line)
        if movq_store_match:
            offset = int(movq_store_match.group(1))
            if offset in offset_to_var:
                var_info = offset_to_var[offset]
                var_name = var_info.get('varName', '')
                var_type = var_info.get('type', 'long')
                # Leer valor de rax (64 bits)
                rax_value = self.regs['rax'] & 0xFFFFFFFFFFFFFFFF
                if rax_value >= 2**63:
                    rax_value_signed = rax_value - 2**64
                else:
                    rax_value_signed = rax_value
                # Actualizar variable (SIEMPRE, incluso si no hay varName en la instrucción)
                if var_name:
                    self.variable_values[var_name] = rax_value_signed
                    print(f"DEBUG _analyze: Actualizando {var_name} = {rax_value_signed} desde movq %rax, {offset}(%rbp)")
                # También actualizar si hay varName en la instrucción (por si acaso)
                if inst_var_name:
                    self.variable_values[inst_var_name] = rax_value_signed
                    print(f"DEBUG _analyze: Actualizando {inst_var_name} = {rax_value_signed} desde varName de instrucción")
                # Actualizar stack
                var_addr = self.regs['rbp'] + offset
                self.stack[var_addr] = rax_value & 0xFFFFFFFFFFFFFFFF
                # Actualizar stack_frame_map
                self._update_stack_frame_map(
                    var_addr,
                    'local_variable',
                    name=var_name or inst_var_name,
                    offset=offset,
                    value=rax_value_signed,
                    var_type=var_type,
                    instruction=first_line
                )
            return
        
        # Analizar movl %eax, offset(%rbp) (guardar en variable)
        mov_store_match = re.match(r'movl\s+%eax,\s*(-?\d+)\(%rbp\)', first_line)
        if mov_store_match:
            offset = int(mov_store_match.group(1))
            if offset in offset_to_var:
                var_info = offset_to_var[offset]
                var_name = var_info.get('varName', '')
                var_type = var_info.get('type', 'int')
                # Leer valor de eax
                eax_value = self.regs['rax'] & 0xFFFFFFFF
                if eax_value >= 2**31:
                    eax_value_signed = eax_value - 2**32
                else:
                    eax_value_signed = eax_value
                # Actualizar variable (SIEMPRE, incluso si no hay varName en la instrucción)
                if var_name:
                    self.variable_values[var_name] = eax_value_signed
                    print(f"DEBUG _analyze: Actualizando {var_name} = {eax_value_signed} desde movl %eax, {offset}(%rbp)")
                # También actualizar si hay varName en la instrucción (por si acaso)
                if inst_var_name:
                    self.variable_values[inst_var_name] = eax_value_signed
                    print(f"DEBUG _analyze: Actualizando {inst_var_name} = {eax_value_signed} desde varName de instrucción")
                # Actualizar stack
                var_addr = self.regs['rbp'] + offset
                self.stack[var_addr] = eax_value & 0xFFFFFFFF
                # Actualizar stack_frame_map
                self._update_stack_frame_map(
                    var_addr,
                    'local_variable',
                    name=var_name or inst_var_name,
                    offset=offset,
                    value=eax_value_signed,
                    var_type=var_type,
                    instruction=first_line
                )
            return
        
        # Analizar movq offset(%rbp), %rax (cargar variable long)
        movq_load_match = re.match(r'movq\s+(-?\d+)\(%rbp\),\s*%rax', first_line)
        if movq_load_match:
            offset = int(movq_load_match.group(1))
            if offset in offset_to_var:
                var_info = offset_to_var[offset]
                var_name = var_info.get('varName', '')
                # PRIORIDAD: Si tenemos el valor en variable_values, usarlo
                if var_name in self.variable_values:
                    var_value = self.variable_values[var_name]
                    var_value_unsigned = var_value if var_value >= 0 else (var_value + 2**64)
                    self.regs['rax'] = var_value_unsigned & 0xFFFFFFFFFFFFFFFF
                # Si no, intentar leer del stack
                else:
                    var_addr = self.regs['rbp'] + offset
                    if var_addr in self.stack:
                        stack_value = self.stack[var_addr] & 0xFFFFFFFFFFFFFFFF
                        if stack_value >= 2**63:
                            stack_value_signed = stack_value - 2**64
                        else:
                            stack_value_signed = stack_value
                        # Actualizar rax
                        self.regs['rax'] = stack_value & 0xFFFFFFFFFFFFFFFF
                        # Actualizar variable_values si no está
                        if var_name and var_name not in self.variable_values:
                            self.variable_values[var_name] = stack_value_signed
            return
        
        # Analizar movl offset(%rbp), %eax (cargar variable)
        mov_load_match = re.match(r'movl\s+(-?\d+)\(%rbp\),\s*%eax', first_line)
        if mov_load_match:
            offset = int(mov_load_match.group(1))
            if offset in offset_to_var:
                var_info = offset_to_var[offset]
                var_name = var_info.get('varName', '')
                # PRIORIDAD: Si tenemos el valor en variable_values, usarlo
                if var_name in self.variable_values:
                    var_value = self.variable_values[var_name]
                    var_value_unsigned = var_value if var_value >= 0 else (var_value + 2**32)
                    self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (var_value_unsigned & 0xFFFFFFFF)
                # Si no, intentar leer del stack
                else:
                    var_addr = self.regs['rbp'] + offset
                    if var_addr in self.stack:
                        stack_value = self.stack[var_addr] & 0xFFFFFFFF
                        if stack_value >= 2**31:
                            stack_value_signed = stack_value - 2**32
                        else:
                            stack_value_signed = stack_value
                        # Actualizar eax
                        self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | stack_value
                        # Actualizar variable
                        self.variable_values[var_name] = stack_value_signed
            return
        
        # Analizar addl %ebx, %eax (suma)
        add_match = re.match(r'addl\s+%ebx,\s*%eax', first_line)
        if add_match:
            eax_value = self.regs['rax'] & 0xFFFFFFFF
            ebx_value = self.regs['rbx'] & 0xFFFFFFFF
            # Si ebx está en 0 pero acabamos de hacer pop, intentar leer del stack
            # El pop elimina el valor del stack, así que necesitamos leer de stack_before_pop
            if ebx_value == 0:
                # pop lee de rsp ANTES de incrementar, así que después del pop, el valor estaba en rsp - 8
                stack_addr = self.regs['rsp'] - 8  # Donde estaba antes del pop
                # Primero intentar leer de stack_before_pop
                if stack_addr in self.stack_before_pop:
                    stack_val = self.stack_before_pop[stack_addr] & 0xFFFFFFFF
                    ebx_value = stack_val
                    # Actualizar rbx también
                    self.regs['rbx'] = (self.regs['rbx'] & 0xFFFFFFFF00000000) | ebx_value
                # Si no está en stack_before_pop, intentar leer del stack actual
                elif stack_addr in self.stack:
                    stack_val = self.stack[stack_addr] & 0xFFFFFFFF
                    ebx_value = stack_val
                    # Actualizar rbx también
                    self.regs['rbx'] = (self.regs['rbx'] & 0xFFFFFFFF00000000) | ebx_value
            if eax_value >= 2**31:
                eax_value_signed = eax_value - 2**32
            else:
                eax_value_signed = eax_value
            if ebx_value >= 2**31:
                ebx_value_signed = ebx_value - 2**32
            else:
                ebx_value_signed = ebx_value
            result = eax_value_signed + ebx_value_signed
            # Actualizar eax
            result_unsigned = result if result >= 0 else (result + 2**32)
            self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (result_unsigned & 0xFFFFFFFF)
            # Si hay varName (ej: suma), actualizar esa variable (crearla si no existe)
            if inst_var_name:
                self.variable_values[inst_var_name] = result
            return
        
        # Analizar imull %ebx, %eax (multiplicación)
        imul_match = re.match(r'imull\s+%ebx,\s*%eax', first_line)
        if imul_match:
            eax_value = self.regs['rax'] & 0xFFFFFFFF
            ebx_value = self.regs['rbx'] & 0xFFFFFFFF
            if eax_value >= 2**31:
                eax_value_signed = eax_value - 2**32
            else:
                eax_value_signed = eax_value
            if ebx_value >= 2**31:
                ebx_value_signed = ebx_value - 2**32
            else:
                ebx_value_signed = ebx_value
            result = eax_value_signed * ebx_value_signed
            # Actualizar eax
            result_unsigned = result if result >= 0 else (result + 2**32)
            self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (result_unsigned & 0xFFFFFFFF)
            # Si hay varName, actualizar esa variable
            if inst_var_name:
                self.variable_values[inst_var_name] = result
            return
        
        # Analizar subl (resta)
        sub_match = re.match(r'subl\s+%ebx,\s*%eax', first_line)
        if sub_match:
            eax_value = self.regs['rax'] & 0xFFFFFFFF
            ebx_value = self.regs['rbx'] & 0xFFFFFFFF
            if eax_value >= 2**31:
                eax_value_signed = eax_value - 2**32
            else:
                eax_value_signed = eax_value
            if ebx_value >= 2**31:
                ebx_value_signed = ebx_value - 2**32
            else:
                ebx_value_signed = ebx_value
            result = eax_value_signed - ebx_value_signed
            # Actualizar eax
            result_unsigned = result if result >= 0 else (result + 2**32)
            self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (result_unsigned & 0xFFFFFFFF)
            # Si hay varName, actualizar esa variable (crearla si no existe)
            if inst_var_name:
                self.variable_values[inst_var_name] = result
            return
        
        # Analizar pushq %reg (guardar en stack)
        push_match = re.match(r'pushq\s+%(\w+)', first_line)
        if push_match:
            reg_name = push_match.group(1)
            # Obtener el valor del registro
            if reg_name == 'rax':
                reg_value = self.regs['rax']
            elif reg_name in self.regs:
                reg_value = self.regs[reg_name]
            else:
                return
            # Asegurarnos de que el stack tenga el valor correcto
            # El emulador ya ejecutó push, que decrementa rsp en 8 y luego guarda el valor
            # Después del push, el valor está en rsp (la dirección actual de rsp)
            stack_addr = self.regs['rsp']  # Después del push, rsp apunta a donde está el valor
            if stack_addr not in self.stack or self.stack[stack_addr] != reg_value:
                # Actualizar el stack manualmente
                self.stack[stack_addr] = reg_value
            # También guardar en stack_before_pop para cuando se haga pop
            # pop lee de rsp ANTES de incrementar, así que después del pop, el valor estaba en rsp
            # Pero después del pop, rsp apunta a la siguiente dirección, así que el valor estaba en rsp - 8
            self.stack_before_pop[stack_addr] = reg_value
            # También guardar en rsp (donde estará rsp después del pop) por si acaso
            self.stack_before_pop[stack_addr + 8] = reg_value
            
            # Solo marcar como temporal si NO es rbp (setup del frame)
            # pushq %rbp es parte del prologue de la función, no es un temporal de operación
            if reg_name != 'rbp':
                # Actualizar stack_frame_map con valor temporal
                # Convertir a signed para el valor (64 bits)
                reg_value_unsigned = reg_value & 0xFFFFFFFFFFFFFFFF
                if reg_value_unsigned >= 2**63:
                    reg_value_signed = reg_value_unsigned - 2**64
                else:
                    reg_value_signed = reg_value_unsigned
                print(f"DEBUG pushq: Guardando temporal en addr=0x{stack_addr:x}, valor={reg_value_signed} (unsigned=0x{reg_value_unsigned:x})")
                self._update_stack_frame_map(
                    stack_addr,
                    'temporary',
                    value=reg_value_signed,
                    source=f'pushq %{reg_name}',
                    step=self.current_step
                )
            else:
                print(f"DEBUG pushq: pushq %rbp es setup del frame, NO es temporal")
            return
        
        # Analizar popq %reg (cargar de stack temporal)
        pop_match = re.match(r'popq\s+%(\w+)', first_line)
        if pop_match:
            reg_name = pop_match.group(1)
            # El emulador ya ejecutó el pop, que lee de rsp y luego incrementa rsp en 8
            # Después del pop, rsp apunta a la siguiente dirección
            # El valor estaba en rsp ANTES del incremento, es decir, en rsp - 8 DESPUÉS del pop
            # Pero pop elimina el valor del stack, así que necesitamos leerlo de stack_before_pop
            stack_addr_after_pop = self.regs['rsp']  # Después del pop
            stack_addr_before_pop = stack_addr_after_pop - 8  # Donde estaba antes del pop
            
            # Buscar el temporal en ambas direcciones posibles
            temp_addr_to_remove = None
            if stack_addr_before_pop in self.stack_frame_map:
                entry = self.stack_frame_map[stack_addr_before_pop]
                if entry.get('type') == 'temporary' and entry.get('status') == 'active':
                    temp_addr_to_remove = stack_addr_before_pop
            elif stack_addr_after_pop in self.stack_frame_map:
                entry = self.stack_frame_map[stack_addr_after_pop]
                if entry.get('type') == 'temporary' and entry.get('status') == 'active':
                    temp_addr_to_remove = stack_addr_after_pop
            
            # Primero intentar leer de stack_before_pop (donde guardamos el valor antes de eliminarlo)
            stack_val = None
            if stack_addr_before_pop in self.stack_before_pop:
                stack_val = self.stack_before_pop[stack_addr_before_pop] & 0xFFFFFFFFFFFFFFFF
            elif stack_addr_after_pop in self.stack_before_pop:
                stack_val = self.stack_before_pop[stack_addr_after_pop] & 0xFFFFFFFFFFFFFFFF
            elif stack_addr_before_pop in self.stack:
                stack_val = self.stack[stack_addr_before_pop] & 0xFFFFFFFFFFFFFFFF
            elif stack_addr_after_pop in self.stack:
                stack_val = self.stack[stack_addr_after_pop] & 0xFFFFFFFFFFFFFFFF
            
            if stack_val is not None:
                # Actualizar el registro correspondiente
                if reg_name == 'rbx':
                    self.regs['rbx'] = stack_val
                elif reg_name == 'rax':
                    self.regs['rax'] = stack_val
                elif reg_name in self.regs:
                    self.regs[reg_name] = stack_val
                print(f"DEBUG popq: Cargando {reg_name} = {stack_val} desde addr=0x{stack_addr_before_pop:x}")
            
            # Eliminar valor temporal del stack_frame_map
            if temp_addr_to_remove is not None:
                print(f"DEBUG popq: Eliminando temporal de addr=0x{temp_addr_to_remove:x}")
                self._remove_temporary_from_map(temp_addr_to_remove)
            return
        
        # Analizar movl offset(%rbp), %eax cuando la variable ya tiene valor conocido
        # (esto es para asegurar que eax tenga el valor correcto incluso si el stack no está actualizado)
        mov_load_match2 = re.match(r'movl\s+(-?\d+)\(%rbp\),\s*%eax', first_line)
        if mov_load_match2:
            offset = int(mov_load_match2.group(1))
            if offset in offset_to_var:
                var_info = offset_to_var[offset]
                var_name = var_info.get('varName', '')
                # Si tenemos el valor en variable_values, usarlo para actualizar eax
                if var_name in self.variable_values:
                    var_value = self.variable_values[var_name]
                    var_value_unsigned = var_value if var_value >= 0 else (var_value + 2**32)
                    self.regs['rax'] = (self.regs['rax'] & 0xFFFFFFFF00000000) | (var_value_unsigned & 0xFFFFFFFF)
            return
    
    def _get_variable_value(self, var_name: str, var_addr: int, var_type: str, 
                           offset: int, instruction_data: Dict[str, Any]) -> Tuple[int, int, str]:
        """
        Obtiene el valor actual de una variable.
        Retorna: (valor_signed, valor_hex, location)
        """
        inst_var_name = instruction_data.get('varName', '')
        inst_asm = instruction_data.get('assembly', '').strip()
        
        # PRIORIDAD 1: Si la variable está en el stack, leer del stack (valor más actualizado)
        # Esto asegura que en bucles, los valores actualizados se reflejen correctamente
        if var_addr in self.stack:
            stack_value = self.stack[var_addr]
            if var_type == 'long':
                if stack_value >= 2**63:
                    var_value_signed = stack_value - 2**64
                else:
                    var_value_signed = stack_value
                var_value = stack_value
            else:
                stack_value_32 = stack_value & 0xFFFFFFFF
                if stack_value_32 >= 2**31:
                    var_value_signed = stack_value_32 - 2**32
                else:
                    var_value_signed = stack_value_32
                var_value = stack_value_32
            var_location = f"stack:0x{var_addr:x}"
            return var_value_signed, var_value, var_location
        
        # PRIORIDAD 2: Si tenemos el valor en variable_values cache (pero no en stack todavía)
        if var_name in self.variable_values:
            var_value_signed = self.variable_values[var_name]
            var_value = var_value_signed if var_value_signed >= 0 else (var_value_signed + (2**64 if var_type == 'long' else 2**32))
            var_location = f"stack:0x{var_addr:x}"
            return var_value_signed, var_value, var_location
        
        var_value_signed = 0
        var_value = 0
        var_location = f"stack:0x{var_addr:x}"
        
        # PRIORIDAD 3: Verificar si la variable está siendo modificada en esta instrucción
        is_current_var = (inst_var_name == var_name or 
                         (inst_var_name and var_name in inst_var_name))
        
        # Verificar si la instrucción escribe a esta dirección de variable
        writes_to_var = False
        if inst_asm:
            # Detectar si la instrucción escribe a esta dirección (ej: movl %eax, -4(%rbp))
            offset_str = f'-{abs(offset)}(%rbp)' if offset < 0 else f'+{offset}(%rbp)'
            if offset_str in inst_asm and ('movl' in inst_asm or 'movq' in inst_asm):
                # Verificar que sea el destino (segundo operando)
                parts = inst_asm.split(',')
                if len(parts) == 2 and offset_str in parts[1]:
                    writes_to_var = True
        
        # Si está siendo modificada en esta instrucción, leer del registro
        if is_current_var or writes_to_var:
            if var_type == 'long':
                var_value = self.regs.get('rax', 0)
                if var_value >= 2**63:
                    var_value_signed = var_value - 2**64
                else:
                    var_value_signed = var_value
            else:
                var_value_raw = self.regs.get('rax', 0) & 0xFFFFFFFF
                var_value = var_value_raw
                if var_value >= 2**31:
                    var_value_signed = var_value - 2**32
                else:
                    var_value_signed = var_value
            var_location = "register:eax" if var_type != 'long' else "register:rax"
        
        # 4. Si la instrucción carga esta variable al registro, leer del registro
        elif inst_asm and f'-{abs(offset)}(%rbp)' in inst_asm:
            if 'movl' in inst_asm or 'movq' in inst_asm:
                if var_type == 'long':
                    var_value = self.regs.get('rax', 0)
                    if var_value >= 2**63:
                        var_value_signed = var_value - 2**64
                    else:
                        var_value_signed = var_value
                else:
                    var_value_raw = self.regs.get('rax', 0) & 0xFFFFFFFF
                    var_value = var_value_raw
                    if var_value >= 2**31:
                        var_value_signed = var_value - 2**32
                    else:
                        var_value_signed = var_value
                var_location = "register:eax" if var_type != 'long' else "register:rax"
        
        return var_value_signed, var_value, var_location
    
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
                        # CORRECCIÓN: offset ya es negativo, entonces rbp + offset es correcto
                        var_addr = rbp + var_offset
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
                # CORRECCIÓN: offset en stackFrame es POSITIVO (4, 8), pero en memoria es NEGATIVO
                # Entonces: var_addr = rbp - offset (no rbp + offset)
                var_addr = rbp_to_use - offset
                
                # Obtener el valor actual de la variable usando la nueva función
                var_value_signed, var_value, var_location = self._get_variable_value(
                    var_name, var_addr, var_type, offset, instruction_data
                )
                
                # Actualizar el rastreo de valores de variables
                self.variable_values[var_name] = var_value_signed
                
                if abs(offset) <= 20:
                    print(f"DEBUG: Variable {var_name}: addr=0x{var_addr:x}, valor={var_value_signed}, location={var_location}, en_stack={var_addr in self.stack}")
                    if var_addr in self.stack:
                        print(f"  Stack[{var_addr:x}] = {self.stack[var_addr]} (raw)")
                
                frame_vars[var_name] = {
                    'value': var_value_signed,
                    'hex': f'0x{var_value:x}',
                    'type': var_type,
                    'address': f'0x{var_addr:x}',
                    'addressDecimal': var_addr,
                    'offset': offset,
                    'initialized': var_addr in self.stack or 'register' in var_location
                }
            call_stack_list.append({
                'function': function_name,
                'rbp': f'0x{rbp:x}',
                'rbpDecimal': rbp,
                'variables': frame_vars,
                'isActive': is_active
            })
        # Generar stack_frame_info desde stack_frame_map
        stack_frame_info = self._generate_stack_frame_info()
        
        # Generar descripción detallada de la instrucción
        instruction_description = self._generate_instruction_description(instruction_data)
        
        return {
            'instruction': instruction_data,
            'registers': registers,
            'stack': stack_list,
            'callStack': call_stack_list,
            'stackFrame': stack_frame_info,
            'instructionDescription': instruction_description,
            'flags': {
                'ZF': self.flags.get('ZF', 0),
                'SF': self.flags.get('SF', 0),
                'CF': self.flags.get('CF', 0),
                'OF': self.flags.get('OF', 0)
            }
        }
    
    def _generate_stack_frame_info(self) -> Dict[str, Any]:
        """
        Genera información del stack frame desde stack_frame_map.
        Separa variables locales de valores temporales.
        Después de leave, solo muestra el return address.
        """
        rbp = self.regs['rbp']
        rsp = self.regs['rsp']
        
        local_variables = []
        temporary_stack = []
        return_address = None
        
        # Si rbp es 0, significa que leave ya se ejecutó y el frame fue destruido
        # En este caso, solo mostrar el return address si existe
        frame_destroyed = (rbp == 0)
        
        if frame_destroyed:
            print(f"DEBUG _generate_stack_frame_info: Frame destruido (rbp=0), solo mostrar return address")
            # Verificar si hay un return address en el stack (después de leave, rsp apunta al return address)
            if rsp in self.stack:
                return_addr_value = self.stack[rsp]
                # Convertir a signed si es necesario
                if return_addr_value >= 2**63:
                    return_addr_signed = return_addr_value - 2**64
                else:
                    return_addr_signed = return_addr_value
                return_address = {
                    'address': f'0x{rsp:x}',
                    'addressDecimal': rsp,
                    'value': return_addr_signed,
                    'label': 'return address'
                }
            
            # Después de leave, NO mostrar variables locales ni temporales
            result = {
                'base_pointer': f'0x{rbp:x}',
                'base_pointerDecimal': rbp,
                'stack_pointer': f'0x{rsp:x}',
                'stack_pointerDecimal': rsp,
                'local_variables': [],  # Vacío después de leave
                'temporary_stack': []  # Vacío después de leave
            }
            
            if return_address:
                result['return_address'] = return_address
            
            print(f"DEBUG _generate_stack_frame_info: Retornando stack frame vacío (después de leave)")
            return result
        
        # Frame activo: procesar normalmente
        # Verificar si hay un return address en el stack
        if rsp in self.stack:
            return_addr_value = self.stack[rsp]
            # Convertir a signed si es necesario
            if return_addr_value >= 2**63:
                return_addr_signed = return_addr_value - 2**64
            else:
                return_addr_signed = return_addr_value
            return_address = {
                'address': f'0x{rsp:x}',
                'addressDecimal': rsp,
                'value': return_addr_signed,
                'label': 'return address'
            }
        
        # Ordenar direcciones de mayor a menor (desde rbp hacia rsp)
        sorted_addrs = sorted(self.stack_frame_map.keys(), reverse=True)
        print(f"DEBUG _generate_stack_frame_info: Procesando {len(sorted_addrs)} entradas en stack_frame_map")
        
        for addr in sorted_addrs:
            if addr not in self.stack_frame_map:
                continue  # Ya fue eliminado
            entry = self.stack_frame_map[addr]
            entry_type = entry.get('type', '')
            
            if entry_type == 'local_variable':
                var_name = entry.get('name', '')
                if var_name:  # Solo incluir si tiene nombre
                    local_variables.append({
                        'name': var_name,
                        'offset': f"{entry.get('offset', 0)}(%rbp)",
                        'address': f'0x{addr:x}',
                        'addressDecimal': addr,
                        'value': entry.get('value', 0),
                        'type': entry.get('var_type', 'int'),
                        'updated_by': entry.get('updated_by', ''),
                        'step': entry.get('step', 0)
                    })
            elif entry_type == 'temporary':
                status = entry.get('status', 'active')
                if status == 'active':  # Solo incluir temporales activos
                    temporary_stack.append({
                        'address': f'0x{addr:x}',
                        'addressDecimal': addr,
                        'value': entry.get('value', 0),
                        'operation': entry.get('source', ''),
                        'step': entry.get('step', 0)
                    })
        
        result = {
            'base_pointer': f'0x{rbp:x}',
            'base_pointerDecimal': rbp,
            'stack_pointer': f'0x{rsp:x}',
            'stack_pointerDecimal': rsp,
            'local_variables': local_variables,
            'temporary_stack': temporary_stack
        }
        
        # Si hay return address, agregarlo
        if return_address:
            result['return_address'] = return_address
        
        return result
    
    def _generate_instruction_description(self, instruction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera una descripción detallada de la instrucción y su efecto en los registros.
        Retorna un diccionario con:
        - description: Descripción textual de qué hace la instrucción
        - registers_read: Lista de registros que se leen
        - registers_written: Lista de registros que se escriben
        - register_changes: Diccionario con los cambios en cada registro (valor anterior -> valor nuevo)
        - memory_operations: Lista de operaciones de memoria (si las hay)
        """
        asm = instruction_data.get('assembly', '').strip()
        if not asm:
            return {
                'description': 'Instrucción no disponible',
                'registers_read': [],
                'registers_written': [],
                'register_changes': {},
                'memory_operations': []
            }
        
        first_line = asm.split('\n')[0].strip()
        
        # Obtener valores de registros ANTES de la instrucción (si están guardados)
        # Si no están guardados, usar los valores actuales como fallback
        if self.registers_before_instruction:
            before_regs = {k: v for k, v in self.registers_before_instruction.items()}
        else:
            before_regs = {k: v for k, v in self.regs.items()}
        
        # Obtener valores actuales de registros DESPUÉS de la instrucción
        current_regs = {k: v for k, v in self.regs.items()}
        
        description = ""
        registers_read = []
        registers_written = []
        register_changes = {}
        memory_operations = []
        
        import re
        
        # movl $inm, %reg
        mov_imm_match = re.match(r'movl\s+\$(-?\d+),\s*%(\w+)', first_line)
        if mov_imm_match:
            value = int(mov_imm_match.group(1))
            reg = mov_imm_match.group(2)
            reg_full = 'rax' if reg == 'eax' else ('rbx' if reg == 'ebx' else reg)
            registers_written.append(reg_full)
            old_value = before_regs.get(reg_full, 0) & 0xFFFFFFFF
            if old_value >= 2**31:
                old_value_signed = old_value - 2**32
            else:
                old_value_signed = old_value
            register_changes[reg_full] = {
                'before': old_value_signed,
                'after': value,
                'hex_before': f'0x{old_value:x}',
                'hex_after': f'0x{value & 0xFFFFFFFF:x}'
            }
            description = f"Carga el valor inmediato {value} en el registro %{reg_full}. %{reg_full} queda con {value}."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # movl %reg1, offset(%rbp) - Guardar en memoria
        mov_store_match = re.match(r'movl\s+%(\w+),\s*(-?\d+)\(%rbp\)', first_line)
        if mov_store_match:
            src_reg = mov_store_match.group(1)
            offset = int(mov_store_match.group(2))
            src_reg_full = 'rax' if src_reg == 'eax' else ('rbx' if src_reg == 'ebx' else src_reg)
            registers_read.append(src_reg_full)
            src_value = before_regs.get(src_reg_full, 0) & 0xFFFFFFFF
            if src_value >= 2**31:
                src_value_signed = src_value - 2**32
            else:
                src_value_signed = src_value
            var_addr = self.regs['rbp'] + offset
            memory_operations.append({
                'type': 'write',
                'address': f'0x{var_addr:x}',
                'addressDecimal': var_addr,
                'offset': f'{offset}(%rbp)',
                'value': src_value_signed,
                'source_register': src_reg_full
            })
            var_name = instruction_data.get('varName', '')
            if var_name:
                description = f"Copia el valor de %{src_reg_full} (que es {src_value_signed}) a la dirección {offset}(%rbp), donde está la variable {var_name}. Almacena {src_value_signed} en {var_name}."
            else:
                description = f"Copia el valor de %{src_reg_full} (que es {src_value_signed}) a la dirección {offset}(%rbp)."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # movl offset(%rbp), %reg - Cargar de memoria
        mov_load_match = re.match(r'movl\s+(-?\d+)\(%rbp\),\s*%(\w+)', first_line)
        if mov_load_match:
            offset = int(mov_load_match.group(1))
            dst_reg = mov_load_match.group(2)
            dst_reg_full = 'rax' if dst_reg == 'eax' else ('rbx' if dst_reg == 'ebx' else dst_reg)
            var_addr = self.regs['rbp'] + offset
            # Leer valor de memoria o variable
            if var_addr in self.stack:
                mem_value = self.stack[var_addr] & 0xFFFFFFFF
                if mem_value >= 2**31:
                    mem_value_signed = mem_value - 2**32
                else:
                    mem_value_signed = mem_value
            else:
                mem_value_signed = 0
            registers_written.append(dst_reg_full)
            old_value = before_regs.get(dst_reg_full, 0) & 0xFFFFFFFF
            if old_value >= 2**31:
                old_value_signed = old_value - 2**32
            else:
                old_value_signed = old_value
            register_changes[dst_reg_full] = {
                'before': old_value_signed,
                'after': mem_value_signed,
                'hex_before': f'0x{old_value:x}',
                'hex_after': f'0x{mem_value_signed & 0xFFFFFFFF:x}'
            }
            memory_operations.append({
                'type': 'read',
                'address': f'0x{var_addr:x}',
                'addressDecimal': var_addr,
                'offset': f'{offset}(%rbp)',
                'value': mem_value_signed
            })
            var_name = instruction_data.get('varName', '')
            if var_name:
                description = f"Carga el valor de la variable {var_name} desde la dirección {offset}(%rbp) en el registro %{dst_reg_full}. %{dst_reg_full} = {var_name} = {mem_value_signed}."
            else:
                description = f"Carga el valor desde la dirección {offset}(%rbp) en el registro %{dst_reg_full}. %{dst_reg_full} = {mem_value_signed}."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # pushq %reg
        push_match = re.match(r'pushq\s+%(\w+)', first_line)
        if push_match:
            reg = push_match.group(1)
            registers_read.append(reg)
            reg_value = before_regs.get(reg, 0)
            if reg_value >= 2**63:
                reg_value_signed = reg_value - 2**64
            else:
                reg_value_signed = reg_value
            stack_addr = current_regs.get('rsp', self.regs['rsp'])  # Después del push
            memory_operations.append({
                'type': 'push',
                'address': f'0x{stack_addr:x}',
                'addressDecimal': stack_addr,
                'value': reg_value_signed,
                'source_register': reg
            })
            registers_written.append('rsp')
            old_rsp = before_regs.get('rsp', self.regs['rsp'])
            new_rsp = current_regs.get('rsp', self.regs['rsp'])
            register_changes['rsp'] = {
                'before': old_rsp,
                'after': new_rsp,
                'hex_before': f'0x{old_rsp:x}',
                'hex_after': f'0x{new_rsp:x}'
            }
            description = f"Decrementa %rsp en 8 y guarda el valor {reg_value_signed} de %{reg} en la pila. %rsp = %rsp - 8."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # popq %reg
        pop_match = re.match(r'popq\s+%(\w+)', first_line)
        if pop_match:
            reg = pop_match.group(1)
            stack_addr = before_regs.get('rsp', self.regs['rsp'])  # Donde estaba antes del pop
            if stack_addr in self.stack_before_pop:
                stack_val = self.stack_before_pop[stack_addr]
            elif stack_addr in self.stack:
                stack_val = self.stack[stack_addr]
            else:
                stack_val = 0
            if stack_val >= 2**63:
                stack_val_signed = stack_val - 2**64
            else:
                stack_val_signed = stack_val
            registers_written.append(reg)
            registers_written.append('rsp')
            old_value = before_regs.get(reg, 0)
            if old_value >= 2**63:
                old_value_signed = old_value - 2**64
            else:
                old_value_signed = old_value
            register_changes[reg] = {
                'before': old_value_signed,
                'after': stack_val_signed,
                'hex_before': f'0x{old_value & 0xFFFFFFFFFFFFFFFF:x}',
                'hex_after': f'0x{stack_val & 0xFFFFFFFFFFFFFFFF:x}'
            }
            old_rsp = before_regs.get('rsp', self.regs['rsp'])
            new_rsp = current_regs.get('rsp', self.regs['rsp'])
            register_changes['rsp'] = {
                'before': old_rsp,
                'after': new_rsp,
                'hex_before': f'0x{old_rsp:x}',
                'hex_after': f'0x{new_rsp:x}'
            }
            memory_operations.append({
                'type': 'pop',
                'address': f'0x{stack_addr:x}',
                'addressDecimal': stack_addr,
                'value': stack_val_signed,
                'destination_register': reg
            })
            description = f"Saca el valor {stack_val_signed} de la pila y lo carga en %{reg}. %{reg} = {stack_val_signed}. %rsp = %rsp + 8."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # addl %reg1, %reg2
        add_match = re.match(r'addl\s+%(\w+),\s*%(\w+)', first_line)
        if add_match:
            src_reg = add_match.group(1)
            dst_reg = add_match.group(2)
            src_reg_full = 'rax' if src_reg == 'eax' else ('rbx' if src_reg == 'ebx' else src_reg)
            dst_reg_full = 'rax' if dst_reg == 'eax' else ('rbx' if dst_reg == 'ebx' else dst_reg)
            registers_read.append(src_reg_full)
            registers_read.append(dst_reg_full)
            registers_written.append(dst_reg_full)
            src_value = before_regs.get(src_reg_full, 0) & 0xFFFFFFFF
            dst_value = before_regs.get(dst_reg_full, 0) & 0xFFFFFFFF
            if src_value >= 2**31:
                src_value_signed = src_value - 2**32
            else:
                src_value_signed = src_value
            if dst_value >= 2**31:
                dst_value_signed = dst_value - 2**32
            else:
                dst_value_signed = dst_value
            result = (dst_value_signed + src_value_signed) & 0xFFFFFFFF
            if result >= 2**31:
                result_signed = result - 2**32
            else:
                result_signed = result
            register_changes[dst_reg_full] = {
                'before': dst_value_signed,
                'after': result_signed,
                'hex_before': f'0x{dst_value:x}',
                'hex_after': f'0x{result:x}'
            }
            description = f"Suma %{src_reg_full} (que es {src_value_signed}) a %{dst_reg_full} (que es {dst_value_signed}). %{dst_reg_full} = %{dst_reg_full} + %{src_reg_full} = {dst_value_signed} + {src_value_signed} = {result_signed}."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # leave
        if first_line.strip() == 'leave':
            registers_read.append('rbp')
            registers_written.append('rsp')
            registers_written.append('rbp')
            old_rsp = before_regs.get('rsp', 0)
            old_rbp = before_regs.get('rbp', 0)
            new_rsp = old_rbp
            # leave hace: movq %rbp, %rsp; popq %rbp
            new_rbp = current_regs.get('rbp', 0)
            register_changes['rsp'] = {
                'before': old_rsp,
                'after': new_rsp,
                'hex_before': f'0x{old_rsp:x}',
                'hex_after': f'0x{new_rsp:x}'
            }
            register_changes['rbp'] = {
                'before': old_rbp,
                'after': new_rbp,
                'hex_before': f'0x{old_rbp:x}',
                'hex_after': f'0x{new_rbp:x}'
            }
            description = "Restaura el stack frame: %rsp = %rbp (deshace la reserva de espacio), luego restaura %rbp desde el stack (pop %rbp)."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # ret
        if first_line.strip() == 'ret':
            registers_read.append('rsp')
            description = "Devuelve el control a la función llamadora. El valor de retorno está en %rax."
            return {
                'description': description,
                'registers_read': registers_read,
                'registers_written': registers_written,
                'register_changes': register_changes,
                'memory_operations': memory_operations
            }
        
        # Instrucción no reconocida
        description = f"Ejecuta la instrucción: {first_line}"
        return {
            'description': description,
            'registers_read': registers_read,
            'registers_written': registers_written,
            'register_changes': register_changes,
            'memory_operations': memory_operations
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
        # Guardar valores de registros ANTES de ejecutar la instrucción (para descripciones)
        emulator.registers_before_instruction = {k: v for k, v in emulator.regs.items()}
        
        # EJECUTAR LA INSTRUCCIÓN - esto actualiza registros y stack
        result = emulator.execute_instruction(asm)
        if emulator.call_stack:
            emulator.call_stack[-1]['rbp'] = emulator.regs['rbp']
        
        # Actualizar variable_values después de ejecutar para rastreo
        if emulator.call_stack:
            active_frame = emulator.call_stack[-1]
            stack_frame_info = active_frame.get('stackFrame', [])
            # Actualizar variable_values leyendo del stack actualizado
            for var_info in stack_frame_info:
                var_name = var_info.get('varName', '')
                if not var_name:
                    continue
                offset = var_info.get('offset', 0)
                var_type = var_info.get('type', 'int')
                # Calcular dirección: offset en stackFrame es positivo (4, 8)
                # pero en memoria las variables están en rbp-offset
                var_addr = emulator.regs['rbp'] - offset
                # Leer del stack si existe
                if var_addr in emulator.stack:
                    stack_value = emulator.stack[var_addr]
                    if var_type == 'long':
                        if stack_value >= 2**63:
                            var_value_signed = stack_value - 2**64
                        else:
                            var_value_signed = stack_value
                    else:
                        stack_value_32 = stack_value & 0xFFFFFFFF
                        if stack_value_32 >= 2**31:
                            var_value_signed = stack_value_32 - 2**32
                        else:
                            var_value_signed = stack_value_32
                    emulator.variable_values[var_name] = var_value_signed
        
        if 'rbp' in first_line.lower() or 'jmp' in first_line.lower() or 'jl' in first_line.lower() or 'jge' in first_line.lower():
            print(f"DEBUG: Antes snapshot - RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}, RSP=0x{emulator.regs['rsp']:x}")
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]}")
        snapshots.append(emulator.get_snapshot({
            'id': inst.get('id', pc),
            'assembly': asm,
            'sourceLine': inst.get('sourceLine', 0),
            'line': inst.get('line', inst.get('sourceLine', 0)),
            'varName': inst.get('varName', ''),  # Incluir varName para rastrear variables
            'cCode': inst.get('cCode', ''),
            'description': inst.get('description', '')
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

