#include <stdio.h>

// 1. Prueba de Recursividad (Stack intensivo)
int factorial(int n) {
    if (n < 2) {
        return 1;
    }
    return n * factorial(n - 1);
}

// 2. Prueba de Paso de Parámetros (4 argumentos)
int suma_cuatro(int a, int b, int c, int d) {
    return a + b + c + d;
}

// 3. Prueba de Flotantes y Aritmética Mixta
float calcular_area(int radio) {
    float pi;
    pi = 3.14159;
    return pi * radio * radio;
}

int main() {
    // Variables locales
    int i;
    int arr[5];
    int total;
    float area;

    printf("=== INICIO DEL TEST ===\n");

    // --- TEST 1: Arrays y Bucles ---
    printf("Test 1: Llenando Array...\n");
    i = 0;
    while (i < 5) {
        arr[i] = i * 10;
        i = i + 1;
    }

    // Imprimir el tercer elemento (debe ser 20)
    printf("arr[2] es: %d\n", arr[2]);

    // --- TEST 2: Recursividad ---
    printf("Test 2: Factorial de 5...\n");
    total = factorial(5);
    printf("Resultado: %d\n", total);
    // Debería ser 120

    // --- TEST 3: Múltiples Parámetros ---
    printf("Test 3: Suma de 10, 20, 30, 40...\n");
    total = suma_cuatro(10, 20, 30, 40);
    printf("Resultado: %d\n", total);
    // Debería ser 100

    // --- TEST 4: Flotantes ---
    printf("Test 4: Area circulo radio 3...\n");
    area = calcular_area(3);

    // Verificación de comparación de floats
    if (area > 28.0) {
        printf("Area correcta: %.2f\n", area);
    } else {
        printf("Error en calculo float\n");
    }

    printf("=== FIN DEL TEST ===\n");
    return 0;
}