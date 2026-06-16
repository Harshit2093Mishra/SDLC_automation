#include "../include/example/calculator.hpp"
#include <gtest/gtest.h>

TEST(Calculator, add_positiveNumbers) {
    EXPECT_EQ(example::Calculator::add(2, 3), 5);
}

TEST(Calculator, safe_divide_nonZeroDenominator) {
    auto result = example::Calculator::safe_divide(10.0, 2.0);
    ASSERT_TRUE(result.has_value());
    EXPECT_DOUBLE_EQ(result.value(), 5.0);
}

TEST(Calculator, safe_divide_zeroDenominator) {
    auto result = example::Calculator::safe_divide(10.0, 0.0);
    EXPECT_FALSE(result.has_value());
}

TEST(Calculator, is_even_evenNumber) {
    EXPECT_TRUE(example::Calculator::is_even(4));
}

TEST(Calculator, is_even_oddNumber) {
    EXPECT_FALSE(example::Calculator::is_even(3));
}