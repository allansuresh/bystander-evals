"""
Small text helpers shared by Data_Collection and Eval_LLMs (no import-time side effects).
"""


def strip_code_fences(text: str) -> str:
    """Remove a surrounding markdown code fence (```json ... ``` or ``` ... ```) if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    # Drop the opening fence line (``` or ```json)
    newline = stripped.find("\n")
    if newline != -1:
        stripped = stripped[newline + 1:]
    else:  # single-line reply like ```json{...}```
        stripped = stripped[3:].lstrip("abcdefghijklmnopqrstuvwxyz")
    # Drop the closing fence
    if stripped.rstrip().endswith("```"):
        stripped = stripped.rstrip()[:-3]
    return stripped.strip()
