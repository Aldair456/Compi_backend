.section .data
    fmt_int: .string "%d\n"
    str_const_11: .string "Alias + Nativo: %d\n"
    str_const_10: .string "Valor Gigante (Long): %ld\n"
    str_const_9: .string "Valor Real (Float): %.4f\n"
    float_const_8: .float 3.141590
    str_const_7: .string "Suma de Enteros: %d\n"
    str_const_6: .string "=== TEST 2: TYPEDEF ===\n"
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .global main

sumar:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movl %edi, -4(%rbp)
    movl %esi, -8(%rbp)
    movl -8(%rbp), %eax
    cltq
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    jmp .end_sumar
.end_sumar:
    leave
    ret

main:
    pushq %rbp
    movq %rsp, %rbp
    subq $32, %rsp
    leaq str_const_6(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $10, %eax
    movl %eax, -4(%rbp)
    movl $20, %eax
    movl %eax, -8(%rbp)
    leaq str_const_7(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -4(%rbp), %eax
    cltq
    movq %rax, %rdi
    movl -8(%rbp), %eax
    cltq
    movq %rax, %rsi
    call sumar
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    movss float_const_8(%rip), %xmm0
    movss %xmm0, -12(%rbp)
    leaq str_const_9(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movss -12(%rbp), %xmm0
    cvtss2sd %xmm0, %xmm0
    popq %rdi
    movq $1, %rax
    call printf@PLT
    xorq %rax, %rax
    movq $9000000000, %rax
    cltq
    movq %rax, -20(%rbp)
    leaq str_const_10(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movq -20(%rbp), %rax
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $5, %eax
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    movl %eax, -24(%rbp)
    leaq str_const_11(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -24(%rbp), %eax
    cltq
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $0, %eax
    jmp .end_main
.end_main:
    leave
    ret

.section .note.GNU-stack,"",@progbits
