
#include <stdio.h>
#include <stdarg.h>
// #include <stdlib.h>

// Reverse a string!
void reverse(char *str, int length)
{
  int start = 0;
  int end = length - 1;
  char tmp;
  while (start < end)
  {
    // Swap:
    tmp = str[start];
    str[start] = str[end];
    str[end] = tmp;

    start++;
    end--;
  }
}

// Integer to ascii:
char* itoa(int value, char* str, int base)
{
  int i = 0, neg = 0;

  // Handle 0 case:
  if (value == 0)
  {
    str[i++] = '0';
    str[i] = '\0';
    return str;
  }

  if (value < 0)
  {
    neg = 1;
    value = -value;
  }

  while (value != 0)
  {
    int rem = value % base;
    char c;
    if (rem < 10)
    {
      c = rem + '0';
    }
    else 
    {
      c = rem - 10 + 'a';
    }
    str[i++] = c;
    value = value / base;
  }

  // Append minus:
  if (neg)
    str[i++] = '-';

  str[i] = 0;

  reverse(str, i);

  return str;
}

static void puts(char* s)
{
  while (*s) bsp_putc(*s++);
}

// Variadic argument function!
int printf(const char* txt, ...)
{
  va_list args;
  va_start(args, txt);
  char buffer[20];

  while (*txt != 0)
  {
    if (*txt == '%')
    {
      txt++; // Consume '%'

      // Parse width:
      while (*txt >= '0' && *txt <= '9')
      {
        txt++;
      }

      // Parse length field:
      while (*txt == 'l')
      {
        txt++;
      }

      // Parse type field:
      if (*txt == 'd')
      {
        txt++;
        int v = va_arg(args, int);
        itoa(v, buffer, 10);
        puts(buffer);
      }
      else if (*txt == 'u')  // unsigned int
      {
        txt++;
        int v = va_arg(args, int);
        itoa(v, buffer, 10);
        puts(buffer);
      }
      else if (*txt == 'x')  // hexadecimal int
      {
        txt++;
        int v = va_arg(args, int);
        itoa(v, buffer, 16);
        puts(buffer);
      }
      else if (*txt == 'c')
      {
        txt++;
        // TODO: how to grab a character from varargs?
        // during calling, it is promoted to integer!
        char c = va_arg(args, int);
        bsp_putc(c);
      }
      else if (*txt == 's')
      {
        txt++;
        char* s = va_arg(args, char*);
        puts(s);
      }
#ifdef __x86_64__
      else if (*txt == 'f')
      {
        txt++;
        double real = va_arg(args, double);
        // TODO: ugh, float formatting?
        itoa((int)real, buffer, 10);
        puts(buffer);
      }
#endif
      else
      {
        txt--;
        bsp_putc(*txt);
        txt++;
        bsp_putc(*txt);
      }
    }
    else
    {
      bsp_putc(*txt);
      txt++;
    }
  }

  va_end(args);
}

