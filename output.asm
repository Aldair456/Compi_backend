.section .data
    fmt_int: .string "%d\n"
    str_const_3: .string "%d\n"
    str_const_2: .string "%d\n"
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .global main

suma:
    pushq %rbp
    movq %rsp, %rbp
    movl %edi, -4(%rbp)
    movl %esi, -8(%rbp)
    movl -8(%rbp), %eax
    cltq
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    addl %ebx, %eax
    jmp .end_suma
.end_suma:
    leave
    ret

resta:
    pushq %rbp
    movq %rsp, %rbp
    movl %edi, -4(%rbp)
    movl %esi, -8(%rbp)
    movl -8(%rbp), %eax
    cltq
    pushq %rax
    movl -4(%rbp), %eax
    cltq
    popq %rbx
    subl %ebx, %eax
    jmp .end_resta
.end_resta:
    leave
    ret

main:
    pushq %rbp
    movq %rsp, %rbp
    subq $16, %rsp
    movl $20, %eax
    movl %eax, -4(%rbp)
    movl $8, %eax
    movl %eax, -8(%rbp)
    leaq str_const_2(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -4(%rbp), %eax
    cltq
    movq %rax, %rdi
    movl -8(%rbp), %eax
    cltq
    movq %rax, %rsi
    call suma
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_3(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl -4(%rbp), %eax
    cltq
    movq %rax, %rdi
    movl -8(%rbp), %eax
    cltq
    movq %rax, %rsi
    call resta
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
