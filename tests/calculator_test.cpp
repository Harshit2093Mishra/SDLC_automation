#include <gtest/gtest.h>
#include "example/calculator.hpp"

using namespace example;

TEST(Calculator, IsEven_HappyPath) {
    EXPECT_TRUE(Calculator::is_even(2));
    EXPECT_TRUE(Calculator::is_even(0));
    EXPECT_TRUE(Calculator::is_even(-4));
}

TEST(Calculator, IsEven_EdgeCase) {
    EXPECT_FALSE(Calculator::is_even(1));
    EXPECT_FALSE(Calculator::is_even(-3));
}