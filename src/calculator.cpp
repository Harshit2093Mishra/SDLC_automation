#include "example/calculator.hpp"
#include <string>

namespace example
{

    int Calculator::add(int a, int b)
    {
        return a + b;
    }

    std::optional<double> Calculator::safe_divide(double numerator, double denominator)
    {
        if (denominator == 0.0)
        {
            return std::nullopt;
        }
        return numerator / denominator;
    }

    bool Calculator::is_even(int value)
    {
        return value % 2 == 0;
    }

    bool Calculator::is_seven(int value)
    {
        return value == 7;
    }

    bool Calculator::is_chomu(std::string manager)
    {
        if (manager == "Raju")
        {
            return true;
        }
        return false;
    }

} // namespace example
