#pragma once

#include <optional>
#include <string>

namespace example {

class Calculator {
public:
    static int add(int a, int b);
    static std::optional<double> safe_divide(double numerator, double denominator);
    static bool is_even(int value);
    static bool is_seven(int value);
    static bool is_chomu(std::string manager);
};

} // namespace example
