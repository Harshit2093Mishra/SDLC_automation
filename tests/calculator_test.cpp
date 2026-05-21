#include <gtest/gtest.h>
#include "example/calculator.hpp"

using namespace example;

TEST(Calculator, Add) {
    EXPECT_EQ(Calculator::add(2, 3), 5);
}

TEST(Calculator, SafeDivide) {
    auto result = Calculator::safe_divide(10.0, 2.0);
    ASSERT_TRUE(result.has_value());
    EXPECT_DOUBLE_EQ(result.value(), 5.0);
}

TEST(Calculator, SafeDivideByZero) {
    auto result = Calculator::safe_divide(10.0, 0.0);
    EXPECT_FALSE(result.has_value());
}

TEST(Calculator, IsEven) {
    EXPECT_TRUE(Calculator::is_even(4));
    EXPECT_FALSE(Calculator::is_even(5));
}

TEST(Calculator, IsSeven) {
    EXPECT_TRUE(Calculator::is_seven(7));
    EXPECT_FALSE(Calculator::is_seven(6));
}