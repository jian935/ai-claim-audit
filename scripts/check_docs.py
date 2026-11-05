#!/usr/bin/env python3
"""Lock the key numbers so the English and Chinese READMEs cannot drift.

    python scripts/check_docs.py

Also asserts the headline numbers appear in the generated eval results, so a
README number can never be a number nobody actually measured.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = (ROOT / "README.md").read_text(encoding="utf-8")
ZH = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
RESULTS = (ROOT / "evals" / "RESULTS.md").read_text(encoding="utf-8")
EXTRAS = (ROOT / "evals" / "EXTRAS_RESULTS.md").read_text(encoding="utf-8")

# Every token must appear in BOTH READMEs. Keep this list to numbers that a
# reader would quote; do not add decorative figures.
TOKENS = [
    "80.0%", "62.7", "90.5", "0.948", "0/10",
    "96.6%", "90.0%", "77.8%", "83.3%",
    "93.9%", "95.8%", "0.966", "0.923",
    "46", "40", "24", "16",
    "0.800", "0.842", "85.7%", "75.0%", "88.9%",
    "71.4%", "2/6", "1/10", "7/7",
]

# Every quoted number must appear in a GENERATED results file, so a README
# figure can never be a number nobody actually measured.
MEASURED = ["80.0%", "0.948", "0/10", "93.9%", "95.8%"]
MEASURED_EXTRAS = [
    "0.800", "0.842", "85.7%", "75.0%", "88.9%", "71.4%", "2/6", "1/10",
]

errors: list[str] = []
for token in TOKENS:
    if token not in EN:
        errors.append(f"README.md missing {token!r}")
    if token not in ZH:
        errors.append(f"README.zh-CN.md missing {token!r}")
for token in MEASURED:
    if token not in RESULTS:
        errors.append(f"evals/RESULTS.md missing {token!r} (README number is unmeasured)")
for token in MEASURED_EXTRAS:
    if token not in EXTRAS:
        errors.append(
            f"evals/EXTRAS_RESULTS.md missing {token!r} (README number is unmeasured)")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    raise SystemExit(1)
print(f"docs consistency: {len(TOKENS)} shared numbers + "
      f"{len(MEASURED) + len(MEASURED_EXTRAS)} measured numbers OK")
