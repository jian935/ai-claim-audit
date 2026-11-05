#!/usr/bin/env python3
"""Score ai-claim-audit's deterministic pre-check against hand-labelled claims.

Zero dependencies, Python 3.10+.

    python scripts/run_evals.py --split dev
    python scripts/run_evals.py --split all --out evals/RESULTS.md
    python scripts/run_evals.py --split all --format json

IMPORTANT: this scores ONLY the six deterministic checks. The other six
rubric checks are semantic and are deliberately NOT auto-scored. A high score
here says nothing about the quality of the model's adjudication.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from audit_claims import MACHINE_CHECKS, CHECKS, precheck_claim  # noqa: E402

EVAL_DIR = ROOT / "evals"
SPLIT_FILES = {"dev": "dev.json", "holdout": "holdout.json"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval; n<8 returns NaN bounds (do not report)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_cases(split: str) -> list[dict]:
    splits = ["dev", "holdout"] if split == "all" else [split]
    cases: list[dict] = []
    for s in splits:
        path = EVAL_DIR / SPLIT_FILES[s]
        if not path.exists():
            if split == "all" and s == "holdout":
                continue  # hold-out is created after dev; dev-only runs are valid
            raise FileNotFoundError(f"missing eval file: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        for c in data["cases"]:
            assert c["split"] == s, f"{c['id']}: split field disagrees with file"
            cases.append(c)
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    return cases


def evaluate(cases: list[dict]) -> dict:
    per = {c: {"tp": 0, "fp": 0, "fn": 0} for c in MACHINE_CHECKS}
    tp = fp = fn = 0
    flawed: list[tuple[dict, set[str]]] = []
    compliant: list[tuple[dict, set[str]]] = []
    mismatches: list[dict] = []

    for case in cases:
        gold = set(case["expected_machine_checks"])
        pred = set(precheck_claim(case["text"]))
        if case["category"] == "compliant":
            assert not gold, f"{case['id']}: compliant case must have empty gold"
            compliant.append((case, pred))
        else:
            flawed.append((case, pred))
        for cid in MACHINE_CHECKS:
            g, p = cid in gold, cid in pred
            if p and g:
                per[cid]["tp"] += 1
                tp += 1
            elif p and not g:
                per[cid]["fp"] += 1
                fp += 1
            elif not p and g:
                per[cid]["fn"] += 1
                fn += 1
        if pred != gold:
            mismatches.append({
                "id": case["id"],
                "category": case["category"],
                "text": case["text"],
                "gold": sorted(gold),
                "pred": sorted(pred),
                "false_positive": sorted(pred - gold),
                "false_negative": sorted(gold - pred),
            })

    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    detected = sum(1 for _, p in flawed if p)
    false_alarms = sum(1 for _, p in compliant if p)
    semantic_only_flawed = sum(1 for c, _ in flawed
                               if not c["expected_machine_checks"])
    semantic_only_detected = sum(1 for c, p in flawed
                                 if not c["expected_machine_checks"] and p)

    return {
        "cases": len(cases),
        "flawed": len(flawed),
        "compliant": len(compliant),
        "semantic_only_flawed": semantic_only_flawed,
        "TP": tp, "FP": fp, "FN": fn,
        "precision": prec,
        "precision_ci": wilson(tp, tp + fp),
        "recall": rec,
        "recall_ci": wilson(tp, tp + fn),
        "f1": f1,
        "claim_detection": detected / len(flawed) if flawed else float("nan"),
        "claim_detection_k": detected,
        "claim_detection_ci": wilson(detected, len(flawed)),
        "false_alarm_rate": false_alarms / len(compliant) if compliant else float("nan"),
        "false_alarm_k": false_alarms,
        "semantic_only_detected": semantic_only_detected,
        "per_check": per,
        "mismatches": mismatches,
    }


def pct(x: float) -> str:
    return "n/a" if math.isnan(x) else f"{x * 100:.1f}%"


def interval(ci: tuple[float, float]) -> str:
    if math.isnan(ci[0]):
        return "n<8, not reported"
    return f"[{ci[0] * 100:.1f}, {ci[1] * 100:.1f}]"


def to_markdown(results: dict[str, dict]) -> str:
    # "all" is the union of the splits; per-check and mismatch tables must use
    # mutually exclusive splits only, otherwise every row is counted twice.
    base = {k: v for k, v in results.items() if k != "all"} or results
    lines = [
        "# Eval results — deterministic pre-check only",
        "",
        "> Scores cover the six machine checks (C01 C05 C06 C09 C10 C12). "
        "The six semantic checks are NOT auto-scored. A clean pre-check is not "
        "evidence that a claim is true.",
        "",
        "| Split | Cases | Flawed | Compliant | TP | FP | FN | Precision [95% CI] | Recall [95% CI] | F1 | Claim detection [95% CI] | False-alarm rate |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for split, r in results.items():
        lines.append(
            f"| {split} | {r['cases']} | {r['flawed']} | {r['compliant']} | "
            f"{r['TP']} | {r['FP']} | {r['FN']} | "
            f"{pct(r['precision'])} {interval(r['precision_ci'])} | "
            f"{pct(r['recall'])} {interval(r['recall_ci'])} | "
            f"{r['f1']:.3f} | "
            f"{pct(r['claim_detection'])} {interval(r['claim_detection_ci'])} | "
            f"{pct(r['false_alarm_rate'])} ({r['false_alarm_k']}/{r['compliant']}) |"
        )
    lines += [
        "",
        "**Claim detection** = share of flawed claims where the pre-check raised "
        "at least one question. It is deliberately lower than the micro metrics: "
        "semantic-only flaws (self-confirming target sets, bad labels, mixed "
        "definitions) have an empty machine gold label, so a correct-but-silent "
        "pre-check counts as a miss. That gap is the point of this table.",
        "",
    ]
    for split, r in results.items():
        if r["semantic_only_flawed"]:
            lines.append(
                f"- {split}: {r['semantic_only_flawed']} semantic-only flawed "
                f"claim(s), {r['semantic_only_detected']} raised any machine "
                f"question — these require model adjudication."
            )
    lines += ["", "## Per-check breakdown", "",
              "| Check | Name | TP | FP | FN | Recall |", "|---|---|---|---|---|---|"]
    for cid in MACHINE_CHECKS:
        # report the union across splits
        tp = sum(r["per_check"][cid]["tp"] for r in base.values())
        fp = sum(r["per_check"][cid]["fp"] for r in base.values())
        fn = sum(r["per_check"][cid]["fn"] for r in base.values())
        rec = tp / (tp + fn) if tp + fn else float("nan")
        lines.append(f"| {cid} | {CHECKS[cid][0]} | {tp} | {fp} | {fn} | {pct(rec)} |")
    lines += ["", "## Mismatches (kept, not patched away)", ""]
    for split, r in base.items():
        for m in r["mismatches"]:
            lines.append(
                f"- `{split}` `{m['id']}` ({m['category']}) "
                f"FP={m['false_positive'] or '—'} FN={m['false_negative'] or '—'} "
                f"— {m['text']}"
            )
    if all(not r["mismatches"] for r in results.values()):
        lines.append("- None. Suspicious: check the eval set for self-confirmation.")
    lines += [
        "",
        "## Limits of this evaluation",
        "",
        "- The dev set was used to design the regex rules. The hold-out file was "
        "written after those rules were frozen, but the same author saw both, "
        "so this is NOT a strictly independent hold-out.",
        "- Gold labels are human judgements of what evidence a sentence supplies; "
        "they are not derived from the script's output. False positives and "
        "false negatives are deliberately left in the set instead of being "
        "patched away; see evals/README.md for the two systematic failure "
        "families the hold-out exposed.",
        "- Sample sizes are small; Wilson intervals are wide. Do not read a "
        "difference of a few points as an improvement.",
        "- No claim is made about the model's adjudication quality.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=("dev", "holdout", "all"), default="all")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cases = load_cases(args.split)
    results: dict[str, dict] = {}
    splits = ["dev", "holdout"] if args.split == "all" else [args.split]
    for s in splits:
        subset = [c for c in cases if c["split"] == s]
        if subset:
            results[s] = evaluate(subset)
    if args.split == "all" and len(results) == 2:
        results["all"] = evaluate(cases)

    if args.format == "json":
        output = json.dumps(results, ensure_ascii=False, indent=2)
    else:
        output = to_markdown(results)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    raise SystemExit(main())
