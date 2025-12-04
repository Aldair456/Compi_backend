.section .data
    fmt_int: .string "%d\n"
    str_const_5: .string "%ld\n"
    str_const_4: .string "%d\n"
    str_const_3: .string "%d\n"
    fmt_float: .string "%.2f\n"
    fmt_long: .string "%ld\n"
.section .bss

.section .text
    .extern printf
    .global main

main:
    pushq %rbp
    movq %rsp, %rbp
    leaq str_const_3(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl $11, %eax
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_4(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl $0, %eax
    movq %rax, %rsi
    popq %rdi
    xorq %rax, %rax
    call printf@PLT
    leaq str_const_5(%rip), %rax
    movq %rax, %rdi
    pushq %rdi
    movl $45, %eax
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
