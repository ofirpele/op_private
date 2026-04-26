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



int main(void) 
{
    char str[MAX_STR_LENGTH+1];
    printf("Please enter string. The string length can't be more than %d\n", MAX_STR_LENGTH);
    read_line(str);
    printf("The Input string:\n %s\n", str);

    printf("The string as recived by the function:\n %s\n", str);

    remove_space(str);

    printf("The string at the end of the function:\n %s\n", str);

    return 0;

}
