"""Rule-based extraction of supported laboratory values from report text.

The parser intentionally stays lightweight and explainable: each supported
parameter has a collection of aliases in ``utils.normal_ranges.PARAMETERS``.
For every parameter we look for a nearby numeric result and classify it using
this project's demonstration interval.

This is not clinical interpretation. Real laboratories may use different
units and reference intervals; the original report's interval takes priority.
"""
from __future__ import annotations

import re
from utils.normal_ranges import PARAMETERS

# Common separators seen after a test name in PDFs / OCR output.
# The numeric capture accepts commas and optional inequality prefixes.
_VALUE = r"(?:[:=\-–—]|\s)\s*(?:result\s*)?(?:[<>]\s*)?([0-9][0-9,]*(?:\.[0-9]+)?)"


def _build_pattern(aliases: list[str]) -> re.Pattern:
    # Wrap every alias in a non-capturing group so aliases containing their own
    # regex groups cannot change which capture contains the numeric value.
    alias_group = "|".join(f"(?:{alias})" for alias in aliases)
    return re.compile(rf"(?:{alias_group})\s*{_VALUE}", re.IGNORECASE)


_COMPILED_PATTERNS = {
    name: _build_pattern(info["aliases"]) for name, info in PARAMETERS.items()
}


def _classify(value: float, info: dict) -> str:
    if value < info["low"]:
        return info["low_label"]
    if value > info["high"]:
        return info["high_label"]
    return "Normal"


def parse_parameters(text: str) -> list[dict]:
    """Return supported laboratory parameters found in *text*.

    When the same parameter occurs multiple times, the first match is used.
    This keeps the behavior deterministic for the dashboard and chatbot.
    """
    if not text:
        return []

    found: list[dict] = []
    for name, pattern in _COMPILED_PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        try:
            value = float(match.group(1).replace(",", ""))
        except (ValueError, TypeError, IndexError):
            continue

        info = PARAMETERS[name]
        found.append(
            {
                "name": name,
                "value": value,
                "unit": info["unit"],
                "normal_range": f"{info['low']} - {info['high']}",
                "status": _classify(value, info),
            }
        )
    return found
