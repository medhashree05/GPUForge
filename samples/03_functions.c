/* Functions and function calls */
static int square(int v) {
    return v * v;
}

int sum_of_squares(int a, int b) {
    return square(a) + square(b);
}

int main(void) {
    return sum_of_squares(3, 4);
}
