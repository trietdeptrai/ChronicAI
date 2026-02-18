"""
Helpers for parsing model JSON responses safely.
"""
import re


def strip_markdown_code_fence(text: str) -> str:
    """
    Remove leading/trailing markdown code fences if present.

    Handles both multiline fences and one-line variants like:
    ```json {"key":"value"} ```
    """
    clean = (text or "").strip()
    if not clean.startswith("```"):
        return clean

    clean = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", clean, count=1)
    clean = re.sub(r"\s*```$", "", clean, count=1)
    return clean.strip()
