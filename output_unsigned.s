.section .data
    fmt_int: .string "%d\n"
    str_const_0: .string "%u\n"
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .global main

    movl $100, %eax
    movl $50, %eax
    leaq str_const_0(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    pushq %rax
    popq %rbx
    addl %ebx, %eax
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    movl $0, %eax
    jmp .end_
.section .note.GNU-stack,"",@progbits
