/* Variables and assignments */
int compute(int a, int b) {
    int sum = a + b;
    int diff = a - b;
    int product = sum * diff;
    product = product + 1;
    return product;
}

int main(void) {
    return compute(7, 3);
}
