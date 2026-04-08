#include <stdio.h>

int main(void)
{
    
    float fahr, celsius;
    int lower, upper, step;
    lower = 0;
    upper = 300;
    step = 20;

    fahr = upper;
    while (fahr >= lower)
    {
        celsius  = (0.5/0.9) * (fahr - 32.0);
        printf("%3.0f %6.1f\n" , fahr, celsius);
        fahr = fahr - step;
    }

    
    return 0;
}
    

    
