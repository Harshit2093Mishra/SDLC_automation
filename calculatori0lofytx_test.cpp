#include <gtest/gtest.h>
#include "example/calculator.hpp"

using namespace example;

TEST(Calculator, IsEven)
{
    Calculator calc;
    EXPECT_TRUE(calc.is_even(4));
}

TEST(Calculator, IsEleven)
{
    Calculator calc;
    EXPECT_TRUE(calc.is_eleven(11));
    EXPECT_FALSE(calc.is_eleven(10));
}
