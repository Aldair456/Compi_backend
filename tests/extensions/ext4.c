// Extensión 4: Type casting (conversión de tipos)
#include <stdio.h>

int main() {
    int x;
    float y;
    float z;
    
    x = 5;
    y = 2.5;
    
    // Conversión explícita: (float)x
    z = (float)x + y;
    
    printf("%.2f\n", z);//7.5
    
    return 0;
}

