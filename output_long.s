.section .data
    fmt_int: .string "%d\n"
    str_const_1: .string "%ld\n"
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
    xorq %rax, %rax
    movq $1000000, %rax
    cltq
    movq %rax, -8(%rbp)
    xorq %rax, %rax
    movq $2000000, %rax
    cltq
    movq %rax, -16(%rbp)
    leaq str_const_1(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movq -16(%rbp), %rax
    pushq %rax
    movq -8(%rbp), %rax
    popq %rbx
    addl %ebx, %eax
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
