"""
Emulador x86-64 en Python puro para ejecutar instrucciones assembly
"""
import re
from typing import Dict, List, Tuple, Any, Optional, Union
import logging

# Configurar el logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class X86Emulator:
    """Emulador de x86-64 en Python puro"""
    
    # Registros 64-bit soportados
    REGISTERS_64BIT = ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
                       'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']
    
    # Registros 32-bit soportados
    REGISTERS_32BIT = ['eax', 'ebx', 'ecx', 'edx', 'edi', 'esi', 'r8d', 'r9d']
    
    # Registros 8-bit soportados (para movzx, movsx, setl, etc.)
    REGISTERS_8BIT = ['al', 'bl', 'cl', 'dl', 'r8b', 'r9b', 'ah', 'bh', 'ch', 'dh']
    
    # Stack inicial
    INITIAL_STACK_POINTER = 0x7fffffffe000
    
    def __init__(self):
        """Inicializa el emulador con registros, flags y stack vacíos"""
        # Registros 64-bit
        self.regs: Dict[str, int] = {
            reg: 0 for reg in self.REGISTERS_64BIT
        }
        self.regs['rsp'] = self.INITIAL_STACK_POINTER
        # Inicializar RBP con el mismo valor que RSP
        # Esto asegura que cuando main hace push rbp, guarda un valor válido
        self.regs['rbp'] = self.INITIAL_STACK_POINTER
        
        # Flags (agregar OF para setl)
        self.flags: Dict[str, int] = {'ZF': 0, 'SF': 0, 'CF': 0, 'OF': 0}
        
        # Stack simulado (dirección -> valor)
        self.stack: Dict[int, int] = {}
        
        # Mapa de labels para saltos
        self.labels: Dict[str, int] = {}
        
        # Call stack: lista de frames activos
        # Cada frame es: {'function': str, 'rbp': int, 'return_pc': int, 'stackFrame': list}
        self.call_stack: List[Dict[str, Any]] = []
        
        # Mapa de funciones a su información de stack frame (del debug_data)
        self.function_frames: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_reg(self, name: str) -> int:
        """Obtiene valor de registro (soporta 64-bit, 32-bit y 8-bit)"""
        if name in self.regs:
            return self.regs[name]
        
        # Registros 32-bit (32 bits bajos de r*)
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
        
        # Registros 8-bit (8 bits bajos de r*)
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
        """Establece valor de registro (sincroniza 64-bit, 32-bit y 8-bit)"""
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
        # Registros 8-bit
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
        """Push al stack"""
        self.regs['rsp'] -= 8
        addr = self.regs['rsp']
        self.stack[addr] = value & 0xFFFFFFFFFFFFFFFF
    
    def pop(self) -> int:
        """Pop del stack"""
        addr = self.regs['rsp']
        value = self.stack.get(addr, 0)
        self.regs['rsp'] += 8
        if addr in self.stack:
            del self.stack[addr]
        return value
    
    def update_flags(self, result: int, size: int = 64) -> None:
        """Actualiza flags ZF, SF, CF basado en resultado"""
        mask = (1 << size) - 1 if size < 64 else 0xFFFFFFFFFFFFFFFF
        result_masked = result & mask
        
        # Zero Flag
        self.flags['ZF'] = 1 if result_masked == 0 else 0
        
        # Sign Flag (bit más significativo)
        sign_bit = (size - 1) if size < 64 else 63
        self.flags['SF'] = 1 if (result_masked >> sign_bit) & 1 else 0
        
        # Carry Flag (CF) - para operaciones aritméticas
        # CF = 1 si hay carry/borrow en la operación
        # Simplificado: si el resultado es negativo en unsigned
        if result < 0:
            self.flags['CF'] = 1
        else:
            self.flags['CF'] = 0
        
        # Overflow Flag (OF) - se calcula específicamente en cada operación
        # Por defecto mantener el valor actual si existe
        if 'OF' not in self.flags:
            self.flags['OF'] = 0
    
    def _get_operand_size(self, operand: Tuple[str, Any]) -> int:
        """Determina el tamaño en bits de un operando"""
        op_type, op_data = operand
        
        if op_type == 'reg':
            reg_name = op_data
            # Registros de 8 bits
            if reg_name in ['al', 'bl', 'cl', 'dl', 'r8b', 'r9b']:
                return 8
            # Registros de 16 bits (no usados comúnmente en x86-64)
            elif reg_name in ['ax', 'bx', 'cx', 'dx']:
                return 16
            # Registros de 32 bits
            elif reg_name in ['eax', 'ebx', 'ecx', 'edx', 'edi', 'esi', 'r8d', 'r9d']:
                return 32
            # Registros de 64 bits
            else:
                return 64
        elif op_type == 'mem':
            # Memoria: asumir 32 bits por defecto (int)
            # Se puede mejorar detectando el tamaño desde la instrucción
            return 32
        else:
            # Inmediato u otro: asumir 32 bits
            return 32
    
    def _sign_extend(self, value: int, from_size: int) -> int:
        """Extiende un valor con signo de from_size bits a 64 bits"""
        if from_size == 8:
            # Extender de 8 a 64 bits
            if value & 0x80:  # Bit 7 es 1 (negativo)
                return value | 0xFFFFFFFFFFFFFF00
            else:
                return value & 0xFF
        elif from_size == 16:
            # Extender de 16 a 64 bits
            if value & 0x8000:  # Bit 15 es 1 (negativo)
                return value | 0xFFFFFFFFFFFF0000
            else:
                return value & 0xFFFF
        elif from_size == 32:
            # Extender de 32 a 64 bits
            if value & 0x80000000:  # Bit 31 es 1 (negativo)
                return value | 0xFFFFFFFF00000000
            else:
                return value & 0xFFFFFFFF
        else:
            # Ya es 64 bits o mayor
            return value & 0xFFFFFFFFFFFFFFFF
    
    def _evaluate_set_condition(self, mnemonic: str) -> bool:
        """Evalúa la condición para instrucciones set* (setl, setg, sete, etc.)"""
        zf = self.flags.get('ZF', 0)
        sf = self.flags.get('SF', 0)
        of = self.flags.get('OF', 0)
        cf = self.flags.get('CF', 0)
        
        if mnemonic == 'sete' or mnemonic == 'setz':
            return zf == 1  # Equal / Zero
        elif mnemonic == 'setne' or mnemonic == 'setnz':
            return zf == 0  # Not Equal / Not Zero
        elif mnemonic == 'setl' or mnemonic == 'setnge':
            return sf != of  # Less (signed)
        elif mnemonic == 'setle' or mnemonic == 'setng':
            return (zf == 1) or (sf != of)  # Less or Equal (signed)
        elif mnemonic == 'setg' or mnemonic == 'setnle':
            return (zf == 0) and (sf == of)  # Greater (signed)
        elif mnemonic == 'setge' or mnemonic == 'setnl':
            return sf == of  # Greater or Equal (signed)
        elif mnemonic == 'setb' or mnemonic == 'setnae' or mnemonic == 'setc':
            return cf == 1  # Below / Carry (unsigned)
        elif mnemonic == 'setbe' or mnemonic == 'setna':
            return (cf == 1) or (zf == 1)  # Below or Equal (unsigned)
        elif mnemonic == 'seta' or mnemonic == 'setnbe':
            return (cf == 0) and (zf == 0)  # Above (unsigned)
        elif mnemonic == 'setae' or mnemonic == 'setnb' or mnemonic == 'setnc':
            return cf == 0  # Above or Equal (unsigned)
        else:
            # Condición desconocida, retornar False
            print(f"Condición set desconocida: {mnemonic}")
            return False
    
    def parse_operand(self, op: str) -> Tuple[str, Any]:
        """Parsea un operando (registro, inmediato, memoria, label)"""
        op = op.strip()
        
        # Registro
        if op in self.regs or op in self.REGISTERS_32BIT or op in self.REGISTERS_8BIT:
            return ('reg', op)
        
        # Inmediato (hex o decimal)
        if op.startswith(('0x', '0X')):
            return ('imm', int(op, 16))
        try:
            return ('imm', int(op))
        except ValueError:
            pass
        
        # Memoria [reg] o [reg+offset] o [reg-offset]
        mem_match = re.match(r'\[([^\]]+)\]', op)
        if mem_match:
            expr = mem_match.group(1)
            # Manejar espacios: "rbp - 4" o "rbp-4"
            expr = expr.replace(' ', '')
            
            # Buscar operador + o -
            if '+' in expr:
                parts = expr.split('+', 1)
                base_reg = parts[0].strip()
                offset = int(parts[1].strip(), 0) if len(parts) > 1 else 0
            elif '-' in expr:
                parts = expr.split('-', 1)
                base_reg = parts[0].strip()
                offset = -int(parts[1].strip(), 0) if len(parts) > 1 else 0
            else:
                # Solo registro, sin offset
                base_reg = expr.strip()
                offset = 0
            
            return ('mem', (base_reg, offset))
        
        # Label
        if op.startswith('.L') or op.endswith(':'):
            return ('label', op.rstrip(':'))
        
        return ('unknown', op)
    
    def get_value(self, operand: Tuple[str, Any]) -> int:
        """Obtiene el valor de un operando"""
        op_type, op_data = operand
        
        if op_type == 'reg':
            return self.get_reg(op_data)
        elif op_type == 'imm':
            return op_data
        elif op_type == 'mem':
            base_reg, offset = op_data
            # IMPORTANTE: Usar el rbp ACTUAL del emulador, no uno guardado
            if base_reg == 'rbp':
                addr = self.regs['rbp'] + offset
            else:
                addr = self.get_reg(base_reg) + offset
            val = self.stack.get(addr, 0)
            # DEBUG: Log lecturas importantes
            if base_reg == 'rbp' and abs(offset) <= 20:
                print(f"DEBUG: Leyendo {val} (0x{val:x}) de [rbp{offset:+d}] = 0x{addr:x}, rbp=0x{self.regs['rbp']:x}")
            return val
        elif op_type == 'label':
            return self.labels.get(op_data, 0)
        
        return 0
    
    def set_value(self, operand: Tuple[str, Any], value: int) -> None:
        """Establece el valor de un operando"""
        op_type, op_data = operand
        
        if op_type == 'reg':
            self.set_reg(op_data, value)
        elif op_type == 'mem':
            base_reg, offset = op_data
            # IMPORTANTE: Usar el rbp ACTUAL del emulador, no uno guardado
            if base_reg == 'rbp':
                addr = self.regs['rbp'] + offset
            else:
                addr = self.get_reg(base_reg) + offset
            # Asegurar que el valor se escriba correctamente
            self.stack[addr] = value & 0xFFFFFFFFFFFFFFFF
            # DEBUG: Log escrituras importantes en memoria
            if base_reg == 'rbp' and abs(offset) <= 20:  # Variables locales típicas
                print(f"DEBUG: Escribiendo {value} (0x{value:x}) en [rbp{offset:+d}] = 0x{addr:x}, rbp=0x{self.regs['rbp']:x}")
    
    def execute_instruction(self, asm_line: str) -> Union[bool, str, Tuple[str, Any]]:
        """Ejecuta una instrucción assembly"""
        asm_line = asm_line.strip()
        
        # Ignorar labels y comentarios
        if not asm_line or asm_line.startswith(';') or asm_line.endswith(':'):
            return True
        
        # Separar mnemónico y operandos
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
        """Ejecuta el mnemónico específico"""
        # MOVIMIENTO
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
            # Move with Sign Extension: extiende signo de fuente pequeña a destino grande
            # movsx rax, eax  - extiende eax (32 bits) a rax (64 bits) con signo
            # movsx eax, al   - extiende al (8 bits) a eax (32 bits) con signo
            if len(operands) == 2:
                src_val = self.get_value(operands[1])
                # Determinar tamaño de fuente basándose en el operando
                src_size = self._get_operand_size(operands[1])
                # Extender con signo
                extended_val = self._sign_extend(src_val, src_size)
                self.set_value(operands[0], extended_val)
            return True
        
        elif mnemonic == 'movzx':
            # Move with Zero Extension: extiende con ceros
            # movzx eax, al   - extiende al (8 bits) a eax (32 bits) con ceros
            if len(operands) == 2:
                src_val = self.get_value(operands[1])
                # Determinar tamaño de fuente
                src_size = self._get_operand_size(operands[1])
                # Extender con ceros (simplemente usar el valor, ya está extendido)
                # Solo asegurar que no tenga bits extra
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
        
        # ARITMÉTICA
        elif mnemonic == 'add':
            if len(operands) == 2:
                # Leer valor actual del destino (puede ser registro o memoria)
                dst_val = self.get_value(operands[0])
                src_val = self.get_value(operands[1])
                result = dst_val + src_val
                # Escribir resultado de vuelta al destino
                self.set_value(operands[0], result)
                self.update_flags(result)
                # DEBUG: Log operaciones add importantes
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
        
        # LÓGICA
        elif mnemonic in ['and', 'or', 'xor']:
            if len(operands) == 2:
                dst_val = self.get_value(operands[0])
                src_val = self.get_value(operands[1])
                if mnemonic == 'and':
                    result = dst_val & src_val
                elif mnemonic == 'or':
                    result = dst_val | src_val
                else:  # xor
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
        
        # COMPARACIÓN
        elif mnemonic == 'cmp':
            if len(operands) == 2:
                val1 = self.get_value(operands[0])
                val2 = self.get_value(operands[1])
                result = val1 - val2
                
                # Actualizar flags basándose en el resultado
                self.update_flags(result, size=64)
                
                # Actualizar OF (Overflow Flag) para comparaciones signed
                # OF = 1 si hay overflow signed en (val1 - val2)
                # Overflow signed ocurre cuando:
                #   - val1 es positivo, val2 es negativo, y resultado es negativo (underflow)
                #   - val1 es negativo, val2 es positivo, y resultado es positivo (overflow)
                # Convertir a signed para detectar signos correctamente
                val1_signed = val1 if val1 < 2**63 else val1 - 2**64
                val2_signed = val2 if val2 < 2**63 else val2 - 2**64
                
                # Overflow signed: los signos de los operandos son diferentes Y
                # el signo del resultado es diferente al signo del primer operando
                val1_positive = val1_signed >= 0
                val2_positive = val2_signed >= 0
                result_positive = result >= 0
                
                if (val1_positive and not val2_positive and not result_positive) or \
                   (not val1_positive and val2_positive and result_positive):
                    self.flags['OF'] = 1
                else:
                    self.flags['OF'] = 0
                
                # DEBUG: Log comparaciones importantes
                print(f"DEBUG: cmp {val1} vs {val2} = {result}, ZF={self.flags['ZF']}, SF={self.flags['SF']}, OF={self.flags['OF']}, CF={self.flags.get('CF', 0)}")
            return True
        
        elif mnemonic == 'test':
            if len(operands) == 2:
                val1 = self.get_value(operands[0])
                val2 = self.get_value(operands[1])
                result = val1 & val2
                self.update_flags(result)
            return True
        
        # STACK
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
        
        # CONTROL
        elif mnemonic == 'nop':
            return True
        
        elif mnemonic == 'leave':
            # leave = mov rsp, rbp; pop rbp
            # Antes de hacer leave, guardar el rbp actual
            old_rbp = self.regs['rbp']
            self.regs['rsp'] = self.regs['rbp']
            self.regs['rbp'] = self.pop()
            
            # Si hay un frame en el call stack con este rbp, eliminarlo
            # (esto sucede cuando se sale de una función)
            if self.call_stack:
                # El frame que se está eliminando debería tener el rbp que acabamos de restaurar
                # Pero como ya hicimos pop, el rbp actual es el del frame anterior
                # Eliminamos el último frame (el que se está saliendo)
                if len(self.call_stack) > 0:
                    self.call_stack.pop()
            
            return True
        
        elif mnemonic == 'call':
            # call = push return_address; jmp target
            if operands:
                return ('call', operands[0])
            return True
        
        elif mnemonic == 'ret':
            # ret = pop rip
            return 'ret'
        
        # SET INSTRUCTIONS (setl, setg, sete, etc.)
        elif mnemonic.startswith('set'):
            # setl, setg, sete, setne, setle, setge, etc.
            if len(operands) == 1:
                # Determinar condición basándose en flags
                condition_met = self._evaluate_set_condition(mnemonic)
                # Guardar 1 o 0 en el registro de destino (8 bits)
                self.set_value(operands[0], 1 if condition_met else 0)
            return True
        
        # SALTOS (se manejan en el loop principal)
        elif mnemonic in ['jmp', 'je', 'jne', 'jl', 'jg', 'jle', 'jge', 'jnz', 'jz']:
            return ('jump', mnemonic, operands[0] if operands else None)
        
        else:
            # Instrucción no implementada, continuar
            print(f"Instrucción no implementada: {mnemonic}")
            return True
    
    def get_snapshot(self, instruction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un snapshot del estado actual del emulador"""
        # Convertir registros a formato de respuesta
        registers = {}
        all_regs = self.REGISTERS_64BIT + self.REGISTERS_32BIT
        for reg_name in all_regs:
            val = self.get_reg(reg_name)
            registers[reg_name] = {
                'hex': f'0x{val:x}',
                'decimal': val if val < 2**63 else val - 2**64
            }
        
        # Convertir stack a formato de respuesta con valores reales
        # Mostrar TODAS las direcciones del stack, no solo las que tienen valores
        stack_list = []
        
        # Obtener rango del stack usado
        if self.stack:
            min_addr = min(self.stack.keys())
            max_addr = max(self.stack.keys())
            # Mostrar desde min_addr hasta rsp (stack pointer actual)
            current_rsp = self.regs['rsp']
            start_addr = min(min_addr, current_rsp)
            end_addr = max(max_addr, current_rsp)
            
            # Mostrar todas las direcciones en el rango (cada 8 bytes para 64-bit)
            for addr in range(start_addr, end_addr + 8, 8):
                val = self.stack.get(addr, 0)
                # Convertir a signed si es necesario
                decimal_val = val if val < 2**63 else val - 2**64
                
                # Determinar qué variable está en esta dirección (si hay frame activo)
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
                    'variable': var_label  # Nombre de variable si existe
                })
        else:
            # Si no hay stack, mostrar al menos el rsp actual
            rsp = self.regs['rsp']
            stack_list.append({
                'address': f'0x{rsp:x}',
                'addressDecimal': rsp,
                'value': '0x0',
                'decimal': 0,
                'variable': None
            })
        
        # Construir call stack con información de frames
        call_stack_list = []
        for i, frame in enumerate(self.call_stack):
            function_name = frame.get('function', 'unknown')
            rbp = frame.get('rbp', 0)
            stack_frame_info = frame.get('stackFrame', [])
            is_active = (i == len(self.call_stack) - 1)
            
            # Construir variables del frame con valores reales
            # IMPORTANTE: Mostrar TODAS las variables, incluso si no están inicializadas
            frame_vars = {}
            
            # DEBUG: Verificar que hay variables en el frame
            if not stack_frame_info:
                print(f"WARNING: Frame {function_name} has no stack_frame_info!")
            
            for var_info in stack_frame_info:
                var_name = var_info.get('varName', '')
                if not var_name:
                    continue  # Saltar si no hay nombre
                    
                offset = var_info.get('offset', 0)
                var_type = var_info.get('type', 'int')
                
                # Calcular dirección: rbp - offset
                # CRÍTICO: SIEMPRE usar el rbp ACTUAL del emulador, NO el del frame
                # El frame puede tener un RBP desactualizado, pero el emulador tiene el correcto
                current_rbp = self.regs['rbp']
                # Ignorar el rbp del frame y usar siempre el actual
                rbp_to_use = current_rbp
                
                var_addr = rbp_to_use - offset
                
                # Leer valor del stack según el tipo
                # IMPORTANTE: Leer directamente del stack, que se preserva entre instrucciones
                if var_type == 'long':
                    # Leer 8 bytes (64 bits)
                    var_value = self.stack.get(var_addr, 0)
                    # Convertir a signed si es necesario
                    if var_value >= 2**63:
                        var_value_signed = var_value - 2**64
                    else:
                        var_value_signed = var_value
                else:
                    # Leer 4 bytes (32 bits) para int o float
                    var_value_raw = self.stack.get(var_addr, 0)
                    # Extraer solo los 32 bits bajos
                    var_value = var_value_raw & 0xFFFFFFFF
                    # Convertir a signed si es necesario
                    if var_value >= 2**31:
                        var_value_signed = var_value - 2**32
                    else:
                        var_value_signed = var_value
                
                # DEBUG: Verificar que el valor se lee correctamente del stack
                if abs(offset) <= 20:  # Variables locales típicas
                    print(f"DEBUG: Variable {var_name}: addr=0x{var_addr:x}, valor={var_value_signed}, en_stack={var_addr in self.stack}, stack_size={len(self.stack)}")
                    if var_addr in self.stack:
                        print(f"  Stack[{var_addr:x}] = {self.stack[var_addr]} (raw)")
                
                # SIEMPRE mostrar la variable, incluso si no está inicializada
                # El frontend puede usar 'initialized' para mostrar "?" o "(sin inicializar)"
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
    """
    Emula la ejecución de instrucciones desde debug.json
    
    Args:
        debug_data: Diccionario con 'instructions' array y 'stackFrame' array
        max_steps: Máximo número de pasos a ejecutar
    
    Returns:
        Array de snapshots con el estado después de cada instrucción
    """
    emulator = X86Emulator()
    instructions = debug_data.get('instructions', [])
    stack_frames_info = debug_data.get('stackFrame', [])
    snapshots = []
    
    # DEBUG CRÍTICO: Verificar que stackFrame existe y tiene datos
    print("=" * 80)
    print("🔥🔥🔥 VERSIÓN NUEVA DEL CÓDIGO - FIX DE LABELS 🔥🔥🔥")
    print("=" * 80)
    print(f"=== DEBUG EMULATOR ===")
    print(f"Debug data keys: {list(debug_data.keys())}")
    print(f"Instructions count: {len(instructions)}")
    print(f"StackFrame count: {len(stack_frames_info)}")
    print(f"StackFrame type: {type(stack_frames_info)}")
    logger.info(f"DEBUG:'")
    # DEBUG: Mostrar estructura completa del debug_data
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
    
    # Mapear labels y funciones
    # CRÍTICO: Los labels DEBEN mapearse ANTES de ejecutar cualquier instrucción
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
    
    # ✅ FIX: PRIMER PASO - Buscar labels que terminan en ':'
    for i, inst in enumerate(instructions):
        asm_raw = inst.get('assembly', '')
        if not asm_raw:
            continue
        
        # Obtener el assembly como string
        asm = str(asm_raw).strip()
        
        # ✅ FIX CRÍTICO: Splitear por líneas primero
        # El assembly puede contener múltiples líneas como "for_start_4:\n    mov eax, 3\n..."
        lines = asm.split('\n')
        first_line = lines[0].strip()  # Solo checkear la primera línea
        
        # DEBUG: Mostrar todas las líneas que podrían ser labels
        if ':' in first_line:
            print(f"DEBUG: Línea {i} primera línea: '{first_line}' (contiene ':')")
        
        # Detectar labels solo en la primera línea
        # Un label es una línea que termina en ':' sin más contenido después
        if first_line.endswith(':'):
            # Extraer el label (remover el ':')
            potential_label = first_line.rstrip(':').strip()
            
            # Agregar el label si no está vacío y no es un comentario
            if potential_label and not potential_label.startswith(';'):
                emulator.labels[potential_label] = i
                print(f"DEBUG: ✅ Label '{potential_label}' mapeado a índice {i}")
                
                # Si el label es un nombre de función (no empieza con prefijos de control de flujo)
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
    
    # DEBUG: Mostrar todos los labels mapeados
    print(f"DEBUG: ✅ Total labels mapeados: {len(emulator.labels)}")
    if emulator.labels:
        print(f"DEBUG: Labels encontrados: {list(emulator.labels.keys())}")
    else:
        print(f"DEBUG: ❌ WARNING - NO SE ENCONTRARON LABELS!")
    
    # Agrupar stack frames por función
    # IMPORTANTE: Siempre asegurar que 'main' existe y tiene todas las variables
    function_vars: Dict[str, List[Dict[str, Any]]] = {}
    
    # Inicializar todas las funciones detectadas
    for func_name in function_start_pc.keys():
        function_vars[func_name] = []
    
    # SIEMPRE asegurar que 'main' existe (aunque no se detecte como label)
    if 'main' not in function_vars:
        function_vars['main'] = []
    
    # IMPORTANTE: Asignar TODAS las variables a TODAS las funciones
    # Esto asegura que cualquier función pueda mostrar sus variables locales
    # El frame activo mostrará las variables correctas basándose en el rbp actual
    for func_name in function_vars.keys():
        # Asignar TODAS las variables a cada función
        # El frame activo filtrará las correctas basándose en el rbp
        function_vars[func_name] = stack_frames_info.copy() if stack_frames_info else []
    
    # DEBUG: Imprimir información para diagnosticar
    print(f"Stack frames info count: {len(stack_frames_info)}")
    print(f"Functions detected: {list(function_vars.keys())}")
    if stack_frames_info:
        print(f"First variable: {stack_frames_info[0] if stack_frames_info else 'None'}")
    
    # Asignar stack frames a funciones
    emulator.function_frames = function_vars
    
    # Inicializar frame de main
    # Asegurar que siempre tenga las variables del stackFrame
    main_stack_frame = emulator.function_frames.get('main', [])
    if not main_stack_frame and stack_frames_info:
        # Si main no tiene variables pero hay stack_frames_info, asignarlas directamente
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
    
    # DEBUG: Verificar que el frame tiene variables
    print(f"Main frame variables count: {len(main_stack_frame)}")
    
    # Snapshot inicial
    if instructions:
        first_inst = instructions[0]
        snapshots.append(emulator.get_snapshot({
            'id': -1,
            'assembly': 'INIT',
            'sourceLine': first_inst.get('sourceLine', 0),
            'line': first_inst.get('line', 0)
        }))
    
    # Ejecutar instrucciones
    pc = 0  # Program counter
    step_count = 0
    
    print(f"DEBUG: Iniciando ejecución con {len(instructions)} instrucciones, max_steps={max_steps}")
    print(f"DEBUG: Labels mapeados: {list(emulator.labels.keys())}")
    
    while pc is not None and pc < len(instructions) and step_count < max_steps:
        inst = instructions[pc]
        asm = inst.get('assembly', '').strip()
        
        # ✅ FIX: Obtener solo la primera línea para procesar
        first_line = asm.split('\n')[0].strip()
        
        # Manejar labels (todos los labels, no solo funciones)
        if first_line.endswith(':'):
            label = first_line.rstrip(':')
            print(f"DEBUG: Procesando label '{label}' en PC={pc}")
            
            # Si es un label de función (no un label de salto interno)
            if label in function_start_pc and label != 'main':
                # Actualizar el frame actual si existe
                if emulator.call_stack:
                    # Buscar si hay un frame para esta función
                    frame_found = False
                    for frame in emulator.call_stack:
                        if frame['function'] == label:
                            frame_found = True
                            break
                    
                    # Si no hay frame, crear uno (esto puede pasar si entramos directamente)
                    if not frame_found:
                        new_frame = {
                            'function': label,
                            'rbp': emulator.regs['rbp'],
                            'return_pc': None,
                            'stackFrame': emulator.function_frames.get(label, [])
                        }
                        emulator.call_stack.append(new_frame)
            
            # CRÍTICO: Saltar el label y ejecutar la siguiente instrucción
            pc += 1
            print(f"DEBUG: Saltando label, nuevo PC={pc}")
            continue
        
        # DEBUG: Log de instrucción a ejecutar (solo primeras líneas o instrucciones importantes)
        if step_count < 10 or 'jmp' in first_line.lower() or 'jl' in first_line.lower() or 'jge' in first_line.lower():
            print(f"DEBUG: Ejecutando PC={pc}: '{first_line}'")
        
        # Ejecutar instrucción
        result = emulator.execute_instruction(asm)
        
        # IMPORTANTE: Actualizar rbp del frame actual SIEMPRE después de cada instrucción
        # Esto asegura que las variables se lean con el rbp correcto
        if emulator.call_stack:
            # Actualizar el rbp del frame activo con el rbp actual del emulador
            emulator.call_stack[-1]['rbp'] = emulator.regs['rbp']
        
        # DEBUG: Verificar estado del stack antes del snapshot
        if 'rbp' in first_line.lower() or 'jmp' in first_line.lower() or 'jl' in first_line.lower() or 'jge' in first_line.lower():
            print(f"DEBUG: Antes snapshot - RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}, RSP=0x{emulator.regs['rsp']:x}")
            # Mostrar algunas direcciones del stack
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]}")
        
        # Generar snapshot después de ejecutar
        # IMPORTANTE: El snapshot debe capturar el estado ACTUAL del emulador
        snapshots.append(emulator.get_snapshot({
            'id': inst.get('id', pc),
            'assembly': asm,
            'sourceLine': inst.get('sourceLine', 0),
            'line': inst.get('line', inst.get('sourceLine', 0))
        }))
        
        step_count += 1
        
        # Manejar call
        if isinstance(result, tuple) and result[0] == 'call':
            pc = _handle_call(emulator, result[1], instructions, pc, debug_data)
            continue
        
        # Manejar saltos
        if isinstance(result, tuple) and result[0] == 'jump':
            old_pc = pc
            # DEBUG: Verificar estado antes del salto
            print(f"DEBUG: ANTES salto - PC={pc}, RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}")
            # Mostrar algunas direcciones del stack antes del salto
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]} (antes salto)")
            
            pc = _handle_jump(emulator, result[1], result[2], instructions, pc)
            
            # CRÍTICO: Actualizar RBP del frame DESPUÉS del salto
            # Esto asegura que el siguiente snapshot use el RBP correcto
            if emulator.call_stack:
                emulator.call_stack[-1]['rbp'] = emulator.regs['rbp']
            
            # DEBUG: Verificar estado después del salto
            print(f"DEBUG: DESPUÉS salto - PC={pc}, RBP=0x{emulator.regs['rbp']:x}, Stack size={len(emulator.stack)}")
            # Mostrar las mismas direcciones del stack después del salto
            for addr in sorted(emulator.stack.keys())[:5]:
                print(f"  Stack[{addr:x}] = {emulator.stack[addr]} (después salto)")
            
            if pc != old_pc + 1:
                print(f"DEBUG: Salto ejecutado: PC {old_pc} -> {pc} ({result[1]})")
                # Verificar qué instrucción se ejecutará en el próximo paso
                if pc < len(instructions):
                    next_inst = instructions[pc].get('assembly', '').strip().split('\n')[0]
                    print(f"DEBUG: Próxima instrucción después del salto (PC={pc}): '{next_inst}'")
            continue
        
        # Manejar ret
        if result == 'ret':
            # Eliminar el frame actual del call stack antes de retornar
            if emulator.call_stack:
                emulator.call_stack.pop()
            pc = _handle_ret(emulator, instructions, pc)
            if pc is None:
                break
            continue
        
        pc += 1
    
    # DEBUG: Verificar por qué terminó el loop
    if pc is None:
        print(f"DEBUG: Loop terminó porque PC se volvió None")
    elif step_count >= max_steps:
        print(f"DEBUG: WARNING - Loop terminó por límite de pasos ({max_steps})")
    elif pc >= len(instructions):
        print(f"DEBUG: Loop terminó porque PC ({pc}) >= len(instructions) ({len(instructions)})")
    else:
        print(f"DEBUG: Loop terminó por otra razón: PC={pc}, step_count={step_count}, max_steps={max_steps}")
    
    # Agregar step number a cada snapshot
    for i, snapshot in enumerate(snapshots):
        snapshot['step'] = i
    
    print(f"Emulated {len(snapshots)} execution snapshots")
    print(f"Execution snapshots generated: {len(snapshots)} steps")
    return snapshots
def _handle_call(emulator: X86Emulator, target_operand: Any, 
                 instructions: List[Dict], pc: int, debug_data: Dict[str, Any] = None) -> int:
    """Maneja una instrucción call"""
    if isinstance(target_operand, tuple) and target_operand[0] == 'label':
        target_label = target_operand[1]
    else:
        target_label = str(target_operand)
    
    # Push dirección de retorno (siguiente instrucción)
    emulator.push(pc + 1)
    
    # Guardar rbp actual antes de la llamada (será el rbp del frame anterior)
    old_rbp = emulator.regs['rbp']
    
    # Encontrar el PC del target
    target_pc = None
    if target_label in emulator.labels:
        target_pc = emulator.labels[target_label]
    else:
        # Buscar en instrucciones
        for i, inst_check in enumerate(instructions):
            asm_check = inst_check.get('assembly', '').strip().rstrip(':')
            if asm_check == target_label or asm_check == target_label + ':':
                target_pc = i
                break
    
    if target_pc is None:
        return pc + 1
    
    # Crear nuevo frame en el call stack
    # El nuevo rbp se establecerá cuando se ejecute "mov rbp, rsp" en el prólogo
    # Por ahora, usamos el rbp actual (que será actualizado después)
    new_frame = {
        'function': target_label,
        'rbp': emulator.regs['rbp'],  # Se actualizará después del prólogo
        'return_pc': pc + 1,
        'stackFrame': emulator.function_frames.get(target_label, [])
    }
    emulator.call_stack.append(new_frame)
    
    return target_pc


def _handle_jump(emulator: X86Emulator, jump_type: str, target_operand: Any,
                 instructions: List[Dict], pc: int) -> int:
    """Maneja una instrucción de salto condicional o incondicional"""
    should_jump = False
    
    zf = emulator.flags.get('ZF', 0)
    sf = emulator.flags.get('SF', 0)
    of = emulator.flags.get('OF', 0)
    cf = emulator.flags.get('CF', 0)
    
    if jump_type == 'jmp':
        should_jump = True
    elif jump_type in ['je', 'jz']:
        should_jump = (zf == 1)  # Equal / Zero
    elif jump_type in ['jne', 'jnz']:
        should_jump = (zf == 0)  # Not Equal / Not Zero
    elif jump_type == 'jl':
        # Jump if Less (signed): SF != OF
        should_jump = (sf != of)
    elif jump_type == 'jle':
        # Jump if Less or Equal (signed): (ZF == 1) || (SF != OF)
        should_jump = (zf == 1) or (sf != of)
    elif jump_type == 'jg':
        # Jump if Greater (signed): (ZF == 0) && (SF == OF)
        should_jump = (zf == 0) and (sf == of)
    elif jump_type == 'jge':
        # Jump if Greater or Equal (signed): SF == OF
        should_jump = (sf == of)
    elif jump_type == 'jb' or jump_type == 'jnae' or jump_type == 'jc':
        # Jump if Below / Carry (unsigned): CF == 1
        should_jump = (cf == 1)
    elif jump_type == 'jbe' or jump_type == 'jna':
        # Jump if Below or Equal (unsigned): (CF == 1) || (ZF == 1)
        should_jump = (cf == 1) or (zf == 1)
    elif jump_type == 'ja' or jump_type == 'jnbe':
        # Jump if Above (unsigned): (CF == 0) && (ZF == 0)
        should_jump = (cf == 0) and (zf == 0)
    elif jump_type == 'jae' or jump_type == 'jnb' or jump_type == 'jnc':
        # Jump if Above or Equal (unsigned): CF == 0
        should_jump = (cf == 0)
    
    # DEBUG: Log saltos
    if target_operand:
        target_str = str(target_operand[1]) if isinstance(target_operand, tuple) else str(target_operand)
        print(f"DEBUG: {jump_type} -> {target_str}, should_jump={should_jump}, ZF={zf}, SF={sf}, OF={of}, CF={cf}")
    
    if not should_jump or not target_operand:
        return pc + 1
    
    # Extraer el nombre del label del operando
    if isinstance(target_operand, tuple):
        if target_operand[0] == 'label':
            target_label = target_operand[1]
        elif len(target_operand) > 1:
            target_label = str(target_operand[1])
        else:
            target_label = str(target_operand[0]) if target_operand else None
    else:
        target_label = str(target_operand)
    
    # Limpiar el label (remover espacios y ':' si los tiene)
    if target_label:
        target_label = target_label.strip().rstrip(':')
    
    print(f"DEBUG: Buscando label '{target_label}' en {len(emulator.labels)} labels mapeados")
    
    # Buscar label en el mapa
    if target_label and target_label in emulator.labels:
        target_pc = emulator.labels[target_label]
        print(f"DEBUG: Label '{target_label}' encontrado en índice {target_pc}")
        # Verificar que el índice es válido
        if target_pc is not None and isinstance(target_pc, int) and 0 <= target_pc < len(instructions):
            next_inst = instructions[target_pc].get('assembly', '').strip()
            print(f"DEBUG: Instrucción en índice {target_pc}: '{next_inst}'")
            # Si es un label, la siguiente instrucción será la que se ejecute
            if next_inst.endswith(':'):
                print(f"DEBUG: Es un label, la siguiente instrucción será ejecutada")
            return target_pc
        else:
            print(f"DEBUG: ERROR - Índice {target_pc} inválido (tipo={type(target_pc)}, len={len(instructions)})")
            # Continuar con búsqueda manual
    
    # Buscar en instrucciones manualmente (fallback)
    print(f"DEBUG: Buscando label '{target_label}' manualmente en instrucciones...")
    for i, inst_check in enumerate(instructions):
        asm_check = inst_check.get('assembly', '').strip()
        # Remover ':' y espacios para comparar
        asm_label = asm_check.rstrip(':').strip()
        if asm_label == target_label or asm_check == target_label + ':' or asm_check == target_label:
            print(f"DEBUG: Label '{target_label}' encontrado manualmente en índice {i}: '{asm_check}'")
            # Agregar al diccionario para futuras búsquedas
            emulator.labels[target_label] = i
            return i
    
    print(f"DEBUG: WARNING - Label '{target_label}' NO encontrado en {len(emulator.labels)} labels")
    print(f"DEBUG: Labels disponibles: {list(emulator.labels.keys())[:20]}")
    # Asegurar que siempre retornamos un int válido
    next_pc = pc + 1 if pc is not None else 0
    print(f"DEBUG: Continuando con PC+1 ({next_pc})")
    return next_pc


def _handle_ret(emulator: X86Emulator, instructions: List[Dict], pc: int) -> Optional[int]:
    """Maneja una instrucción ret"""
    print(f"DEBUG: ret - RSP=0x{emulator.regs['rsp']:x}, RBP=0x{emulator.regs['rbp']:x}")
    print(f"DEBUG: ret - Stack size: {len(emulator.stack)}")
    
    # El epilogue (mov rsp, rbp y pop rbp) ya debería haberse ejecutado antes
    # Solo necesitamos hacer pop de la dirección de retorno si hay algo en el stack
    # y el RSP está por debajo del stack inicial (hay algo en el stack)
    if emulator.regs['rsp'] < X86Emulator.INITIAL_STACK_POINTER:
        # Hay algo en el stack, intentar hacer pop de la dirección de retorno
        try:
            return_addr = emulator.pop()
            print(f"DEBUG: ret - Popped return address: 0x{return_addr:x} (PC={return_addr})")
            if isinstance(return_addr, int) and 0 <= return_addr < len(instructions):
                return return_addr
        except (KeyError, IndexError):
            # Stack vacío o error, terminar ejecución
            print(f"DEBUG: ret - Stack vacío o error al hacer pop, terminando ejecución")
            pass
    
    # Fin de ejecución (ya sea porque no hay dirección de retorno o porque es main)
    print(f"DEBUG: ret - Finalizando ejecución")
    print(f"DEBUG: ret - RBP final: 0x{emulator.regs['rbp']:x}, RSP final: 0x{emulator.regs['rsp']:x}")
    return None

