"""
LLM interaction: prompt template filling and response parsing.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from unit_test_automation.config import PROMPT_TEMPLATE, BUILD_FIX_PROMPT, EVAL_SCRIPT


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------
def _indent_block(code: str, indent: str = "      ") -> str:
    if not code:
        return ""
    return "\n".join(indent + line for line in code.splitlines())


def fill_prompt_template(
    template_path: Path,
    substitutions: dict[str, str],
) -> Path:
    """
    Read *template_path*, replace ``{{key}}`` placeholders, write to a
    temp file and return its path.
    """
    text = template_path.read_text()
    for key, value in substitutions.items():
        text = text.replace(f"{{{{{key}}}}}", value)

    tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=template_path.suffix)
    tmp.write(text)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
def parse_llm_json(raw: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from raw LLM / ``gh models eval`` output.

    ``gh models eval --json`` wraps the model response in:
      { "testResults": [{ "modelResponse": "<json string>" }] }

    We must always unwrap this before returning, otherwise callers receive
    the wrapper dict (with keys like ``totalTests``) instead of the model's
    actual JSON payload.

    Tries, in order:
    1. Parse as JSON; if it looks like a gh-models wrapper, unwrap it.
    2. If direct parse succeeded and is NOT a wrapper, return it.
    3. Brute-force first ``{`` ... last ``}`` extraction.
    """
    parsed = None
    try:
        parsed = json.loads(raw)
    except Exception:
        pass

    if parsed is not None:
        # Check if this is a gh models eval wrapper
        # Use 'or []' not default arg — handles both missing key AND explicit null value
        if "testResults" in parsed:
            for entry in (parsed.get("testResults") or []):
                if not isinstance(entry, dict):
                    continue
                mr = entry.get("modelResponse") or entry.get("output")
                if not mr:
                    continue
                # modelResponse may itself be a JSON string or may contain one
                try:
                    return json.loads(mr)
                except Exception:
                    pass
                try:
                    start = mr.index("{")
                    end = mr.rindex("}") + 1
                    return json.loads(mr[start:end])
                except Exception:
                    continue
            # It was a wrapper but had no valid model responses — return None
            return None
        # Not a wrapper — return it directly (already the model JSON)
        return parsed

    # Not valid JSON at all — brute-force extract first {...} block
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------
def generate_tests(
    source_file: str,
    suggested_test_file: str,
    header_code: str,
    impl_code: str,
    diff_content: str = "",
    existing_test_code: str = "",
) -> Optional[dict]:
    """
    Call the LLM to generate unit tests.  Returns the parsed JSON response
    or ``None`` on failure.
    """
    prompt_path = fill_prompt_template(
        PROMPT_TEMPLATE,
        {
            "source_file": source_file,
            "suggested_test_file": suggested_test_file,
            "header_code": _indent_block(header_code),
            "implementation_code": _indent_block(impl_code),
            "diff_content": _indent_block(diff_content) if diff_content else "(full file provided above — no incremental diff available)",
            "existing_test_code": _indent_block(existing_test_code) if existing_test_code else "(no existing tests)",
        },
    )
    try:
        result = subprocess.run(
            [str(EVAL_SCRIPT), str(prompt_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"[ERROR] eval script failed: {result.stderr}")
            return None
        out = result.stdout
    except (FileNotFoundError, OSError) as exc:
        print(f"[ERROR] Could not run eval script ({EVAL_SCRIPT}): {exc}")
        print("[INFO] The eval script requires bash + gh CLI. Run in a Linux/Codespaces environment.")
        return None
    finally:
        prompt_path.unlink(missing_ok=True)

    parsed = parse_llm_json(out)
    if parsed is None:
        print(f"[ERROR] Failed to parse LLM JSON. Output was:\n{out[:500]}")
    return parsed


def generate_build_fix(build_output: str) -> Optional[dict]:
    """
    Ask the LLM for source edits that fix compilation errors.

    Returns parsed JSON with ``edits``, ``blockers``, ``summary`` keys,
    or ``None`` on failure.
    """
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
        json.dump({"build_output": build_output}, tf)
        tf.flush()
        input_path = tf.name

    try:
        result = subprocess.run(
            [str(EVAL_SCRIPT), str(BUILD_FIX_PROMPT), input_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, OSError) as exc:
        Path(input_path).unlink(missing_ok=True)
        print(f"[ERROR] Could not run eval script: {exc}")
        return None
    finally:
        Path(input_path).unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"[ERROR] AI fixer failed. Stderr:\n{result.stderr}")
        return None

    parsed = parse_llm_json(result.stdout)
    if parsed is None:
        print(f"[ERROR] Failed to parse AI response:\n{result.stdout[:500]}")
    return parsed
