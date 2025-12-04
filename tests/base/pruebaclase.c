// test_typedef.c
#include <stdio.h>

// Definición de Alias
typedef int Entero;
typedef float Real;
typedef long Gigante;

// Funciones usando Alias
Entero sumar(Entero a, Entero b) {
    return a + b;
}

int main() {
    Entero x;
    Entero y;
    Real radio;
    Gigante distancia;

    printf("=== TEST 2: TYPEDEF ===\n");

    // Usando alias como si fueran tipos nativos
    x = 10;
    y = 20;
    printf("Suma de Enteros: %d\n", sumar(x, y));

    radio = 3.14159;
    printf("Valor Real (Float): %.4f\n", radio);

    distancia = 9000000000;
    printf("Valor Gigante (Long): %ld\n", distancia);

    // Mezcla de alias y tipos nativos (deben ser compatibles)
    int z;
    z = x + 5;
    printf("Alias + Nativo: %d\n", z);

    return 0;
}