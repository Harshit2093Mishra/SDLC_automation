"""
LLM interaction: prompt template filling and response parsing.

Key design:
* The bash eval script is NO LONGER used for inference.
  gh models run is called directly via subprocess, which avoids all
  shell quoting / read-splitting bugs.
* The bash script (run_prompt_eval.sh) is kept only for manual
  standalone debugging.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from unit_test_automation.config import PROMPT_TEMPLATE, BUILD_FIX_PROMPT


# ---------------------------------------------------------------------------
# Internal: invoke the model
# ---------------------------------------------------------------------------
def _load_prompt_yaml(path: Path) -> tuple[str, str, str]:
    """
    Parse a filled prompt YAML and return (model, system_msg, user_msg).

    Requires PyYAML (``pip install pyyaml``).
    """
    try:
        import yaml
    except ImportError:
        raise RuntimeError(
            "PyYAML is required: run 'pip install pyyaml' or "
            "'pip install -r requirements.txt'"
        )
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    model = doc.get("model", "openai/gpt-4o-mini")
    system_msg = ""
    user_msg = ""
    for msg in doc.get("messages", []):
        role = msg.get("role", "")
        content = str(msg.get("content", ""))
        if role == "system":
            system_msg = content
        elif role == "user":
            user_msg = content

    return model, system_msg, user_msg


def _invoke_model(model: str, system_msg: str, user_msg: str) -> Optional[str]:
    """
    Call ``gh models run`` for a single inference.

    * model      — e.g. ``openai/gpt-4o-mini``
    * system_msg — system prompt (passed via --system flag)
    * user_msg   — user turn (piped to stdin)

    Returns raw model output string or None on failure.
    """
    cmd = ["gh", "models", "run", model]
    if system_msg:
        cmd += ["--system-prompt", system_msg]

    try:
        result = subprocess.run(
            cmd,
            input=user_msg,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"[ERROR] gh models run failed (exit {result.returncode}):")
            print(result.stderr[:800])
            return None
        output = result.stdout.strip()
        if not output:
            print("[ERROR] gh models run returned empty output.")
            print(f"[DEBUG] stderr: {result.stderr[:400]}")
            return None
        return output
    except FileNotFoundError:
        print("[ERROR] 'gh' CLI not found. Install from https://cli.github.com/")
        print("[INFO]  Also run: gh extension install github/gh-models")
        return None
    except OSError as exc:
        print(f"[ERROR] Could not run 'gh': {exc}")
        return None


# ---------------------------------------------------------------------------
# Prompt template helpers
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
    text = template_path.read_text(encoding="utf-8")
    for key, value in substitutions.items():
        text = text.replace(f"{{{{{key}}}}}", value)

    tmp = tempfile.NamedTemporaryFile(
        "w", delete=False, suffix=template_path.suffix, encoding="utf-8"
    )
    tmp.write(text)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` wrappers that models sometimes add."""
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text.strip())
    return text.strip()


def parse_llm_json(raw: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from raw LLM output.

    Handles:
    1. ``gh models eval`` wrapper: { "testResults": [...] } — unwrap
    2. Markdown-fenced JSON: ```json{...}``` — strip fences then parse
    3. Plain JSON — parse directly
    4. JSON embedded in prose — brute-force { ... } extraction
    """
    if not raw or not raw.strip():
        return None

    cleaned = _strip_markdown_fences(raw)

    # Try to parse (fence-stripped first, then original)
    parsed = None
    for candidate in (cleaned, raw):
        try:
            parsed = json.loads(candidate)
            break
        except Exception:
            pass

    if parsed is not None:
        # Unwrap gh models eval wrapper if present
        if "testResults" in parsed:
            for entry in (parsed.get("testResults") or []):
                if not isinstance(entry, dict):
                    continue
                mr = entry.get("modelResponse") or entry.get("output")
                if not mr:
                    continue
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
            return None
        return parsed

    # Brute-force: extract first complete {...} block
    for text in (cleaned, raw):
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# Public LLM calls
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
    Generate unit tests via the LLM. Returns parsed JSON or None on failure.
    """
    prompt_path = fill_prompt_template(
        PROMPT_TEMPLATE,
        {
            "source_file": source_file,
            "suggested_test_file": suggested_test_file,
            "header_code": _indent_block(header_code),
            "implementation_code": _indent_block(impl_code),
            "diff_content": (
                _indent_block(diff_content)
                if diff_content
                else "(full file provided above — no incremental diff available)"
            ),
            "existing_test_code": (
                _indent_block(existing_test_code)
                if existing_test_code
                else "(no existing tests)"
            ),
        },
    )
    try:
        model, system_msg, user_msg = _load_prompt_yaml(prompt_path)
    except Exception as exc:
        print(f"[ERROR] Failed to load prompt YAML: {exc}")
        prompt_path.unlink(missing_ok=True)
        return None
    finally:
        prompt_path.unlink(missing_ok=True)

    out = _invoke_model(model, system_msg, user_msg)
    if not out:
        return None

    parsed = parse_llm_json(out)
    if parsed is None:
        print(f"[ERROR] Failed to parse LLM JSON. Output was:\n{out[:500]}")
    return parsed


def generate_build_fix(build_output: str) -> Optional[dict]:
    """
    Ask the LLM for source edits that fix compilation errors.

    Returns parsed JSON with ``edits``, ``blockers``, ``summary`` keys,
    or None on failure.
    """
    # Embed the build output directly into the user message via template
    prompt_path = fill_prompt_template(
        BUILD_FIX_PROMPT,
        {
            "build_output": build_output[:4000],   # cap to avoid huge prompts
        },
    )
    try:
        model, system_msg, user_msg = _load_prompt_yaml(prompt_path)
    except Exception as exc:
        print(f"[ERROR] Failed to load build fix prompt YAML: {exc}")
        prompt_path.unlink(missing_ok=True)
        return None
    finally:
        prompt_path.unlink(missing_ok=True)

    out = _invoke_model(model, system_msg, user_msg)
    if not out:
        return None

    parsed = parse_llm_json(out)
    if parsed is None:
        print(f"[ERROR] Failed to parse AI response:\n{out[:500]}")
    return parsed
