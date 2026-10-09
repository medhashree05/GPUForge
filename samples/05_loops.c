/* Loops */
int sum_to(int n) {
    int total = 0;
    for (int i = 1; i <= n; i++) {
        total += i;
    }
    return total;
}

int count_down(int n) {
    int steps = 0;
    while (n > 0) {
        n = n / 2;
        steps++;
    }
    return steps;
}

int main(void) {
    return sum_to(10) + count_down(64);
}
