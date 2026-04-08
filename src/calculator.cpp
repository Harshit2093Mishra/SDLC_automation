#include "example/calculator.hpp"

namespace example {

int Calculator::add(int a, int b) {
    return a + b;
}

std::optional<double> Calculator::safe_divide(double numerator, double denominator) {
    if (denominator == 0.0) {
        return std::nullopt;
    }
    return numerator / denominator;
}

bool Calculator::is_even(int value) {
    return value % 2 == 0;
}

} // namespace example
