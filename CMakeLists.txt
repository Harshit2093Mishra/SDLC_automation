cmake_minimum_required(VERSION 3.14)
project(cpp_unit_test_agent_mvp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

# ── production library ────────────────────────────────────────────────
file(GLOB_RECURSE LIB_SOURCES CONFIGURE_DEPENDS "src/*.cpp" "src/*.cc" "src/*.cxx")

add_library(project_lib ${LIB_SOURCES})

target_include_directories(project_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# ── GoogleTest ────────────────────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# ── test targets (auto-discovered) ────────────────────────────────────
file(GLOB TEST_SOURCES CONFIGURE_DEPENDS "tests/*_test.cpp" "tests/*_test.cc")

if(TEST_SOURCES)
    add_executable(all_tests ${TEST_SOURCES})

    target_link_libraries(all_tests
        PRIVATE
            project_lib
            GTest::gtest_main
    )

    include(GoogleTest)
    gtest_discover_tests(all_tests)
endif()
