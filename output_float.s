.section .data
    fmt_int: .string "%d\n"
    str_const_5: .string "%.2f\n"
    float_const_4: .float 2.860000
    float_const_3: .float 3.140000
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
    movss float_const_3(%rip), %xmm0
    movss %xmm0, -4(%rbp)
    movss float_const_4(%rip), %xmm0
    movss %xmm0, -8(%rbp)
    movss -8(%rbp), %xmm0
    subq $8, %rsp
    movss %xmm0, (%rsp)
    movss -4(%rbp), %xmm0
    movss (%rsp), %xmm1
    addq $8, %rsp
    addss %xmm1, %xmm0
    movss %xmm0, -12(%rbp)
    leaq str_const_5(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movss -12(%rbp), %xmm0
    cvtss2sd %xmm0, %xmm0
    popq %rdi
    movq $1, %rax
    call printf@PLT
    movl $0, %eax
    jmp .end_main
.end_main:
    leave
    ret

.section .note.GNU-stack,"",@progbits
