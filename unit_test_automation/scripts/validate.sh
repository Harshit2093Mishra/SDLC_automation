#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR="${BUILD_DIR:-build}"
BUILD_TYPE="${BUILD_TYPE:-Debug}"
GENERATOR="${GENERATOR:-Ninja}"

printf '\n[1/3] Configure\n'
cmake -S . -B "$BUILD_DIR" -G "$GENERATOR" -DCMAKE_BUILD_TYPE="$BUILD_TYPE" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

printf '\n[2/3] Build\n'
cmake --build "$BUILD_DIR" --parallel --clean-first

printf '\n[3/3] Test\n'
ctest --test-dir "$BUILD_DIR" --output-on-failure

printf '\nValidation completed successfully.\n'
