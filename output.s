.section .data
    fmt_int: .string "%d\n"
    str_const_5: .string "%d\n"
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .globl main

main:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movl $0, %eax
    movl %eax, -4(%rbp)
    movl $0, %eax
    movl %eax, -8(%rbp)
while_start_3:
    movl $5, %eax
    pushq %rax
    movl -8(%rbp), %eax
    cltq
    popq %rbx
    cmpl %ebx, %eax
    setl %al
    movzbq %al, %rax
    testq %rax, %rax
    jz while_end_4
    movl -8(%rbp), %eax
    cltq
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    movl %eax, -4(%rbp)
    movl $1, %eax
    pushq %rax
    movl -8(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    movl %eax, -8(%rbp)
    jmp while_start_3
while_end_4:
    leaq str_const_5(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -4(%rbp), %eax
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
