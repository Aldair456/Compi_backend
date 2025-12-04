.section .data
    fmt_int: .string "%d\n"
    str_const_1: .string "%u\n"
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
    movl $100, %eax
    movl %eax, -4(%rbp)
    movl $50, %eax
    movl %eax, -8(%rbp)
    leaq str_const_1(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -8(%rbp), %eax
    pushq %rax
    movl -4(%rbp), %eax
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
