#include <gtest/gtest.h>
#include "example/calculator.hpp"

TEST(Calculator, Add) {
    EXPECT_EQ(example::Calculator::add(2, 3), 5);
    EXPECT_EQ(example::Calculator::add(-1, 1), 0);
}

TEST(Calculator, SafeDivide) {
    EXPECT_EQ(example::Calculator::safe_divide(10.0, 2.0), 5.0);
    EXPECT_EQ(example::Calculator::safe_divide(5.0, 0.0), std::nullopt);
}

TEST(Calculator, SafeDivideByZero) {
    EXPECT_EQ(example::Calculator::safe_divide(10.0, 0.0), std::nullopt);
}

TEST(Calculator, IsEven) {
    EXPECT_TRUE(example::Calculator::is_even(2));
    EXPECT_FALSE(example::Calculator::is_even(3));
}

TEST(Calculator, IsOdd) {
    EXPECT_FALSE(example::Calculator::is_even(3));
    EXPECT_TRUE(example::Calculator::is_even(4));
}

TEST(Calculator, IsSeven) {
    EXPECT_TRUE(example::Calculator::is_seven(7));
    EXPECT_FALSE(example::Calculator::is_seven(6));
}

TEST(Calculator, IsNotSeven) {
    EXPECT_FALSE(example::Calculator::is_seven(8));
    EXPECT_TRUE(example::Calculator::is_seven(7));
}