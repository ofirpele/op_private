#include <stdio.h>
#include <ctype.h>
#define MAX_STR_LENGTH 4

void read_line(char s[])
{
    int c,i;
    for(i=0; i<MAX_STR_LENGTH; i++)
    {
        c = getchar();
        if (c == '\n')
        {
            break;
        }
        s[i] = c;
    }
    s[i] = '\0';
}

void remove_space(char str[])
{
    int read_i = 0;
    int write_i = 0; 
    for(; str[read_i] != '\0' && read_i<MAX_STR_LENGTH; read_i++)
    {
        if(!isspace(str[read_i]))
        {
            str[write_i] = str[read_i];
            write_i++;
        }
    }
    str[write_i] = '\0';
}

void print_in_binary(long n) 
{
    int num_of_bits = sizeof(long) * 8;

    for (int i = num_of_bits - 1; i >= 0; i--) 
    {
        long bit = (n >> i) & 1;
        printf("%ld", bit);
    }
    printf("\n");

}

long turn_on(long num)
{
    return ( num | (1L << 17));
}


int main(void) 
{
    printf("please enter number :) \n");
    long num;
    scanf("%ld", &num);
    printf("The original number in binary:  ");
    print_in_binary(num);
    printf("The original number in base 10: %ld \n", num);
    long new_num;
    new_num = turn_on(num);
    printf("After turning on bit 17, a change was made: ");
    print_in_binary(new_num);
    printf("The number in base 10 after the change:%ld \n", new_num);
   
    printf("--------------\n");
    char str[MAX_STR_LENGTH+1];
    printf("Please enter string. The string length can't be more than %d\n", MAX_STR_LENGTH);
    read_line(str);
    printf("The Input string:\n %s\n", str);

    printf("The string as recived by the function:\n %s\n", str);

    remove_space(str);

    printf("The string at the end of the function:\n %s\n", str);

    return 0;

}
 