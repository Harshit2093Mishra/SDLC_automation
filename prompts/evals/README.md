# Prompt evaluation seed cases

This folder contains seed cases for the C++ unit test generator prompt.

## Intended use

- keep a small deterministic set of code snippets for prompt tuning
- add one JSON object per line to `unit_test_generator_cases.jsonl`
- mirror especially tricky patterns from your production codebase over time

## Suggested evaluation process

1. Edit `prompts/unit_test_generator.prompt.yml`.
2. Run:

   ```bash
   gh models eval prompts/unit_test_generator.prompt.yml --json
   ```

3. Review structure, blockers, and whether the generated `test_code` is plausible.
4. For top prompts, compile generated code in a temp branch before promoting the prompt change.
