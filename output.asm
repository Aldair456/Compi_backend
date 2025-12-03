section .data
    fmt_int: db "%d", 10, 0
    fmt_float: db "%.2f", 10, 0
    fmt_long: db "%ld", 10, 0

section .bss

section .text
    extern printf
    global main

main:
    push rbp
    mov rbp, rsp
    mov eax, -445
    mov rsp, rbp
    pop rbp
    ret

