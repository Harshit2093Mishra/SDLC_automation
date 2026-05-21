#include <gtest/gtest.h>
#include "example/calculator.hpp"

using namespace example;

TEST(Calculator, Add) {
    EXPECT_EQ(Calculator::add(2, 3), 5);
    EXPECT_EQ(Calculator::add(-1, 1), 0);
}

TEST(Calculator, SafeDivide) {
    EXPECT_EQ(Calculator::safe_divide(10.0, 2.0).value(), 5.0);
    EXPECT_FALSE(Calculator::safe_divide(10.0, 0.0).has_value());
}

TEST(Calculator, IsEven) {
    EXPECT_TRUE(Calculator::is_even(2));
    EXPECT_FALSE(Calculator::is_even(3));
}

TEST(Calculator, IsSeven) {
    EXPECT_TRUE(Calculator::is_seven(7));
    EXPECT_FALSE(Calculator::is_seven(8));
}