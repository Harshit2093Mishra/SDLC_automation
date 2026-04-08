#include <gtest/gtest.h>

#include "example/calculator.hpp"

using example::Calculator;

TEST(CalculatorTest, AddHandlesPositiveNumbers) {
    EXPECT_EQ(Calculator::add(20, 22), 42);
}

TEST(CalculatorTest, SafeDivideReturnsQuotientForValidInput) {
    auto result = Calculator::safe_divide(10.0, 2.0);
    ASSERT_TRUE(result.has_value());
    EXPECT_DOUBLE_EQ(*result, 5.0);
}

TEST(CalculatorTest, SafeDivideReturnsNulloptOnZeroDenominator) {
    auto result = Calculator::safe_divide(10.0, 0.0);
    EXPECT_FALSE(result.has_value());
}

TEST(CalculatorTest, IsEvenDetectsEvenAndOddValues) {
    EXPECT_TRUE(Calculator::is_even(4));
    EXPECT_FALSE(Calculator::is_even(5));
}
