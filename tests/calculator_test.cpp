#include <gtest/gtest.h>
#include "example/calculator.hpp"

using namespace example;

TEST(Calculator, Add)
{
    Calculator calc;
    EXPECT_EQ(calc.add(2, 3), 5);
}

TEST(Calculator, SafeDivide)
{
    Calculator calc;
    EXPECT_EQ(calc.safe_divide(10.0, 2.0).value(), 5.0);
    EXPECT_EQ(calc.safe_divide(10.0, 0.0), std::nullopt);
}

TEST(Calculator, IsEven)
{
    Calculator calc;
    EXPECT_TRUE(calc.is_even(4));
    EXPECT_FALSE(calc.is_even(5));
}

TEST(Calculator, IsChomu)
{
    Calculator calc;
    EXPECT_TRUE(calc.is_chomu("Raju"));
    EXPECT_FALSE(calc.is_chomu("John"));
}

TEST(Calculator, MinEatingSpeed)
{
    std::vector<int> piles = {3, 6, 7, 11};
    EXPECT_EQ(Calculator::minEatingSpeed(piles, 8), 4);
    EXPECT_EQ(Calculator::minEatingSpeed(piles, 11), 3);
}

TEST(Calculator, CalculateFinalCartPrice_EmptyCart)
{
    Calculator calc;
    EXPECT_THROW({ calc.calculateFinalCartPrice({}, "SAVE10", false, "KA"); }, std::invalid_argument);
}

TEST(Calculator, CalculateFinalCartPrice_UnsupportedStateCode)
{
    Calculator calc;
    std::vector<CartItem> items = {{"1", 1, 100.0}};
    EXPECT_THROW({ calc.calculateFinalCartPrice(items, "SAVE10", false, "XX"); }, std::invalid_argument);
}

TEST(Calculator, CalculateFinalCartPrice_NegativeUnitPrice)
{
    Calculator calc;
    std::vector<CartItem> items = {{"1", 1, -100.0}};
    EXPECT_THROW({ calc.calculateFinalCartPrice(items, "SAVE10", false, "KA"); }, std::invalid_argument);
}

TEST(Calculator, CalculateFinalCartPrice_ValidCalculation)
{
    Calculator calc;
    std::vector<CartItem> items = {{"1", 10, 100.0}};
    PricingResult result = calc.calculateFinalCartPrice(items, "SAVE10", true, "KA");
    EXPECT_DOUBLE_EQ(result.subtotal, 950.0);
    EXPECT_NEAR(result.discount, 142.5, 1e-6);
    EXPECT_NEAR(result.tax, 145.35, 1e-6);
    EXPECT_NEAR(result.total, 952.85, 1e-6);
}

TEST(Calculator, IsEleven)
{
    Calculator calc;
    EXPECT_TRUE(calc.is_eleven(11));
}

TEST(Calculator, IsEleven_NotEleven)
{
    Calculator calc;
    EXPECT_FALSE(calc.is_eleven(10));
    EXPECT_FALSE(calc.is_eleven(12));
}
