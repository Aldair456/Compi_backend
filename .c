.section .data
    fmt_int: .string "%d\n"
    str_const_37: .string "=== FIN DEL TEST ===\n"
    str_const_36: .string "Error en calculo float\n"
    str_const_35: .string "Area correcta: %.2f\n"
    float_const_34: .float 28.000000
    str_const_31: .string "Test 4: Area circulo radio 3...\n"
    str_const_30: .string "Resultado: %d\n"
    str_const_29: .string "Test 3: Suma de 10, 20, 30, 40...\n"
    str_const_28: .string "Resultado: %d\n"
    str_const_27: .string "Test 2: Factorial de 5...\n"
    str_const_26: .string "arr[2] es: %d\n"
    str_const_23: .string "Test 1: Llenando Array...\n"
    str_const_22: .string "=== INICIO DEL TEST ===\n"
    float_const_5: .float 3.141590
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .global main

factorial:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movl %edi, -4(%rbp)
    movl $2, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    cmpl %ebx, %eax
    setl %al
    movzbq %al, %rax
    testq %rax, %rax
    jz endif_3
    movl $1, %eax
    jmp .end_factorial
endif_3:
    movl $1, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    subl %ebx, %eax
    movq %rax, %rdi
    call factorial
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    imull %ebx, %eax
    jmp .end_factorial
.end_factorial:
    leave
    ret

suma_cuatro:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movl %edi, -4(%rbp)
    movl %esi, -8(%rbp)
    movl %edx, -12(%rbp)
    movl %ecx, -16(%rbp)
    movl -16(%rbp), %eax
    cltq
    pushq %rax
    movl -12(%rbp), %eax
    cltq
    pushq %rax
    movl -8(%rbp), %eax
    cltq
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    popq %rbx
    addl %ebx, %eax
    popq %rbx
    addl %ebx, %eax
    jmp .end_suma_cuatro
.end_suma_cuatro:
    leave
    ret

calcular_area:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movl %edi, -4(%rbp)
    movss float_const_5(%rip), %xmm0
    movss %xmm0, -8(%rbp)
    movl -4(%rbp), %eax
    cltq
    cvtsi2ssl %eax, %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movl -4(%rbp), %eax
    cltq
    cvtsi2ssl %eax, %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movss -8(%rbp), %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    mulss %xmm1, %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    mulss %xmm1, %xmm0
    jmp .end_calcular_area
.end_calcular_area:
    leave
    ret

main:
    pushq %rbp
    movq %rsp, %rbp
    subq $32, %rsp
    leaq str_const_22(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_23(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $0, %eax
    movl %eax, -4(%rbp)
while_start_24:
    movl $5, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    cmpl %ebx, %eax
    setl %al
    movzbq %al, %rax
    testq %rax, %rax
    jz while_end_25
    movl $10, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    imull %ebx, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    imulq $4, %rax
    movq %rbp, %rbx
    subq $24, %rbx
    addq %rax, %rbx
    popq %rax
    movl %eax, (%rbx)
    movl $1, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    movl %eax, -4(%rbp)
    jmp while_start_24
while_end_25:
    leaq str_const_26(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl $2, %eax
    imulq $4, %rax
    movq %rbp, %rbx
    subq $24, %rbx
    addq %rax, %rbx
    movl (%rbx), %eax
    cltq
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_27(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $5, %eax
    movq %rax, %rdi
    call factorial
    movl %eax, -28(%rbp)
    leaq str_const_28(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -28(%rbp), %eax
    cltq
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_29(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $10, %eax
    movq %rax, %rdi
    movl $20, %eax
    movq %rax, %rsi
    movl $30, %eax
    movq %rax, %rdx
    movl $40, %eax
    movq %rax, %rcx
    call suma_cuatro
    movl %eax, -28(%rbp)
    leaq str_const_30(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -28(%rbp), %eax
    cltq
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_31(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $3, %eax
    movq %rax, %rdi
    call calcular_area
    movss %xmm0, -32(%rbp)
    movss float_const_34(%rip), %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movss -32(%rbp), %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    ucomiss %xmm1, %xmm0
    seta %al
    movzbq %al, %rax
    testq %rax, %rax
    jz else_32
    leaq str_const_35(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movss -32(%rbp), %xmm0
    cvtss2sd %xmm0, %xmm0
    popq %rdi
    movq $1, %rax
    call printf@PLT
    jmp endif_33
else_32:
    leaq str_const_36(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
endif_33:
    leaq str_const_37(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $0, %eax
    jmp .end_main
.end_main:
    leave
    ret

.section .note.GNU-stack,"",@progbits
