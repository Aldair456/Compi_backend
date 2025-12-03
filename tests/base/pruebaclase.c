#include <stdio.h>

// Función auxiliar para valor absoluto (Float)
float absoluto(float n) {
    if (n < 0.0) {
        return 0.0 - n; // Truco para negar float: 0.0 - x
    }
    return n;
}

// Algoritmo para calcular Raíz Cuadrada
float raiz_cuadrada(float n) {
    float x;
    float nuevo_x;
    float error;
    int iter;

    // Suposición inicial: la mitad del número
    x = n / 2.0;
    iter = 0;

    // Iteramos hasta encontrar la precisión o máximo 20 veces
    while (iter < 20) {
        // Fórmula de Newton: x = 0.5 * (x + n/x)
        nuevo_x = 0.5 * (x + n / x);

        // Calculamos cuánto cambió (error)
        error = absoluto(nuevo_x - x);

        // Si el error es muy pequeño (0.0001), ya terminamos
        if (error < 0.0001) {
            // Truco: Forzamos la salida del while haciendo iter grande
            iter = 100;
        } else {
            // Seguimos refinando
            x = nuevo_x;
            iter = iter + 1;
        }
    }
    return x;
}

int main() {
    float num;
    float res;

    printf("=== CALCULO DE RAIZ CUADRADA (NEWTON) ===\n");

    // Caso 1: Raíz exacta
    num = 16.0;
    res = raiz_cuadrada(num);
    printf("Raiz de %.2f = %.4f\n", num, res);

    // Caso 2: Raíz irracional (sqrt(2))
    num = 2.0;
    res = raiz_cuadrada(num);
    printf("Raiz de %.2f = %.4f\n", num, res);

    // Caso 3: Número grande
    num = 100.0;
    res = raiz_cuadrada(num);
    printf("Raiz de %.2f = %.4f\n", num, res);

    return 0;
}