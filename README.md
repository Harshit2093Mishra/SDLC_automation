# C++ Unit Test Agent MVP (Week 1 Scaffold)

This repository gives you a ready-to-use Week 1 starting point for a C++-only, unit-test-generation MVP on GitHub Codespaces.

## What is included

- GitHub Codespaces / devcontainer setup
- CMake + GoogleTest sample C++ project
- PR diff collector for changed C++ files
- Validation script for configure/build/test
- GitHub Actions validation workflow
- GitHub Models prompt file for unit-test generation
- Seed evaluation cases for prompt iteration
- Prebuild configuration guide

## Quick start

### 1) Open in GitHub Codespaces

From GitHub:

- push this repository
- click **Code** -> **Codespaces** -> **Create codespace on main**

The devcontainer will install the required tooling and pre-configure the sample build directory.

### 2) Build and run tests

```bash
bash scripts/validate.sh
```

### 3) Inspect changed C++ files in a branch or PR range

```bash
python3 scripts/collect_pr_diff.py --base origin/main --head HEAD
```

### 4) Run prompt evaluation locally (if GitHub Models is enabled)

```bash
gh extension install github/gh-models || true
gh models eval prompts/unit_test_generator.prompt.yml --json
```

## Repository layout

```text
.
├── .devcontainer/
├── .github/workflows/
├── include/example/
├── src/
├── tests/
├── prompts/
│   └── evals/
└── scripts/
```

## Sample C++ target

The sample library is intentionally tiny so you can validate the workflow immediately:

- `example::Calculator::add`
- `example::Calculator::safe_divide`
- `example::Calculator::is_even`

## How to adapt this to your real codebase

1. Replace the sample `include/`, `src/`, and `tests/` folders with your real project.
2. Update `CMakeLists.txt` so `project_lib` points to your actual library or binary targets.
3. Keep `scripts/collect_pr_diff.py`, `scripts/validate.sh`, the prompt files, and the workflow.
4. When the unit test agent is ready, wire it to write new files under `tests/` and then call `scripts/validate.sh`.

## Enabling Codespaces prebuilds

See `docs/codespaces-prebuilds.md`.

## Notes

- The prompt file is designed to return **strict JSON** so the next step (Week 2) can parse model output safely.
- The evaluation cases are intentionally small and deterministic to help you compare prompt changes.
