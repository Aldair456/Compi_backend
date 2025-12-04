.section .data
    fmt_int: .string "%d\n"
    str_const_15: .string "Comparison works\n"
    float_const_14: .float 4.500000
    str_const_11: .string "Result 2: %.2f\n"
    float_const_10: .float 2.500000
    str_const_9: .string "Result: %.2f\n"
    float_const_8: .float 4.500000
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .global main

main:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movss float_const_8(%rip), %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movl $3, %eax
    cvtsi2ssl %eax, %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    addss %xmm1, %xmm0
    movss %xmm0, -4(%rbp)
    leaq str_const_9(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movss -4(%rbp), %xmm0
    cvtss2sd %xmm0, %xmm0
    popq %rdi
    movq $1, %rax
    call printf@PLT
    movl $10, %eax
    movl %eax, -8(%rbp)
    movss float_const_10(%rip), %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movl -8(%rbp), %eax
    cltq
    cvtsi2ssl %eax, %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    addss %xmm1, %xmm0
    movss %xmm0, -12(%rbp)
    leaq str_const_11(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movss -12(%rbp), %xmm0
    cvtss2sd %xmm0, %xmm0
    popq %rdi
    movq $1, %rax
    call printf@PLT
    movss float_const_14(%rip), %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movl $3, %eax
    cvtsi2ssl %eax, %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    ucomiss %xmm1, %xmm0
    setb %al
    movzbq %al, %rax
    testq %rax, %rax
    jz endif_13
    leaq str_const_15(%rip), %rax
    movq %rax, %rdi
    xorq %rax, %rax
    call printf@PLT
endif_13:
    movl $0, %eax
    jmp .end_main
.end_main:
    leave
    ret

.section .note.GNU-stack,"",@progbits
