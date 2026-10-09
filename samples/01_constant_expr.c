/* Arithmetic and constant expressions.
   Compare -O0 and -O2: does the addition survive? */
int main(void) {
    int x = 10 + 20;
    int y = x * 2 - 5;
    return y;
}
