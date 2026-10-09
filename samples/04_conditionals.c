/* Conditional statements, including a constant condition */
int classify(int n) {
    if (n < 0)
        return -1;
    else if (n == 0)
        return 0;
    return 1;
}

int main(void) {
    int debug = 0;
    int result = classify(42);
    if (debug) {          /* condition is a known constant */
        result = result * 100;
    }
    return result;
}
