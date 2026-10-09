/* Unused and redundant computations */
int work(int a) {
    int unused = a * 1000;        /* never read            */
    int t1 = a * 4;
    int t2 = a * 4;               /* same as t1            */
    int zero = a - a;             /* algebraically zero    */
    int k = 3 * 7;                /* constant              */
    if (1 > 2) {                  /* never true            */
        t1 = t1 + 99;
    }
    return t1 + t2 + zero + k;
}

int main(void) {
    return work(5);
}
