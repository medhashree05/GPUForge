// A small C++ program: class, template, and reference parameters
#include <cstdio>

template <typename T>
T clamp_value(T v, T lo, T hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

class Counter {
public:
    void add(int v) { total_ += v; }
    int total() const { return total_; }
private:
    int total_ = 0;
};

int main() {
    Counter c;
    for (int i = 0; i < 5; ++i)
        c.add(clamp_value(i * 3, 0, 10));
    std::printf("%d\n", c.total());
    return 0;
}
