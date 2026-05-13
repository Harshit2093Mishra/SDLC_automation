cmake_minimum_required(VERSION 3.14)
project(cpp_unit_test_agent_mvp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

target_include_directories(project_lib
add_library(project_lib
    src/calculator.cpp
)

target_include_directories(project_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/unit_test_automation/include
)

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_executable(calculator_tests
    tests/calculator_test.cpp
)

target_link_libraries(calculator_tests
    PRIVATE
        project_lib
        GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(calculator_tests)
