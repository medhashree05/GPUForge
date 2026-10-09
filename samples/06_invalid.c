/* Intentionally invalid program: several semantic and syntax errors */
int add(int a, int b) {
    return a + b;
}

int main(void) {
    int x = 5
    int y = undeclared_var + 1;
    int z = add(1);
    char *p = 42;
    return x + y;
}
