#!/usr/bin/env python3
"""Semantic-adjudication and trigger-precision eval suites.

Zero dependencies, Python 3.10+.

    python scripts/eval_extras.py --suite all --out evals/EXTRAS_RESULTS.md
    python scripts/eval_extras.py --suite semantic --predictions my_model.json
    python scripts/eval_extras.py --self-test

WHAT THIS SCORES
    Two suites that the main regex pre-check cannot cover:
      semantic.json  20 cases with structured `material` and human gold labels
                     for the six semantic checks (C02 C03 C04 C07 C08 C11).
      trigger.json   20 user messages labelled by INTENT for should/should-not
                     trigger.

    By default a DETERMINISTIC BASELINE is scored. It is the control group,
    not the model. To score real model output, pass --predictions with a JSON
    mapping case id -> list of check ids (semantic) or bool (trigger).
    This repo never fabricates a model-adjudication score.
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
from run_evals import wilson, pct, interval  # noqa: E402

SUITE_FILES = {"semantic": "semantic.json", "trigger": "trigger.json"}
SEMANTIC_CHECKS = ("C02", "C03", "C04", "C07", "C08", "C11")
TRIGGER_KEY = "T"

TRIGGER_HINTS = (
    "审", "查一下", "看看", "能写进", "能引用", "对不上", "能信", "自证",
    "问穿", "哪里不对", "口径", "有没有问题", "帮我判断",
)
BLOCK_HINTS = (
    "写一版", "设计", "翻译", "算一下", "正则", "润色", "是不是真的",
    "竞品分析", "天气", "多少",
)


def load_cases(suite: str) -> list[dict]:
    data = json.loads((ROOT / "evals" / SUITE_FILES[suite]).read_text(encoding="utf-8"))
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), f"duplicate ids in {suite}"
    return cases


def baseline_semantic(material: dict) -> set[str]:
    """Shallow, deterministic reading of the structured material only.

    Deliberately cannot read `text`. Four hidden-contradiction cases exist to
    keep its recall below 1.00, and two compliant traps keep precision below
    1.00. That gap is the space model adjudication has to earn.
    """
    raised: set[str] = set()
    tsd = str(material.get("target_set_definition") or "")
    if any(k in tsd for k in ("正文含", "模型预测", "自身输出")):
        raised.add("C02")
    label = str(material.get("label_source") or "")
    if any(k in label for k in ("搜索词", "采集时", "队列状态", "算法分数")):
        raised.add("C03")
    split = str(material.get("split") or "").lower()
    if not split or any(k in split for k in ("未拆分", "全量", "none", "single")):
        raised.add("C04")
    definition = material.get("metric_definition_source")
    if isinstance(definition, list) and len({str(x) for x in definition}) > 1:
        raised.add("C07")
    elif isinstance(definition, str) and any(
            k in definition for k in ("不一致", "多处", "硬编码")):
        raised.add("C07")
    if (material.get("dedup_by_body") is False
            or material.get("boilerplate_stripped") is False):
        raised.add("C08")
    if len(material.get("slices_reported") or []) <= 1:
        raised.add("C11")
    return raised


def baseline_trigger(text: str) -> bool:
    if any(k in text for k in BLOCK_HINTS):
        return False
    return any(k in text for k in TRIGGER_HINTS)


def baseline_predictions(suite: str, cases: list[dict]) -> dict[str, set[str]]:
    if suite == "semantic":
        return {c["id"]: baseline_semantic(c["material"]) for c in cases}
    return {c["id"]: ({TRIGGER_KEY} if baseline_trigger(c["text"]) else set())
            for c in cases}


def normalize_predictions(raw: dict, suite: str,
                          cases: list[dict]) -> dict[str, set[str]]:
    if suite in raw and isinstance(raw[suite], dict):
        raw = raw[suite]
    ids = {c["id"] for c in cases}
    out: dict[str, set[str]] = {}
    for cid, value in raw.items():
        if cid not in ids:
            continue
        if suite == "semantic":
            out[cid] = set(value) if isinstance(value, list) else set()
        else:
            hit = value is True or value == TRIGGER_KEY or value == [TRIGGER_KEY]
            out[cid] = {TRIGGER_KEY} if hit else set()
    missing = ids - set(out)
    if missing:
        raise ValueError(
            f"predictions missing {len(missing)} case(s): {sorted(missing)[:6]}")
    return out


def load_predictions(path: Path, suite: str,
                     cases: list[dict]) -> dict[str, set[str]]:
    return normalize_predictions(
        json.loads(path.read_text(encoding="utf-8")), suite, cases)


def score(suite: str, cases: list[dict], predictions: dict[str, set[str]],
          source: str) -> dict:
    items = SEMANTIC_CHECKS if suite == "semantic" else (TRIGGER_KEY,)
    per = {i: {"tp": 0, "fp": 0, "fn": 0} for i in items}
    tp = fp = fn = tn = 0
    flawed = compliant = detected = false_alarms = 0
    mismatches: list[dict] = []

    for case in cases:
        if suite == "semantic":
            gold = set(case["expected_semantic_checks"])
        else:
            gold = {TRIGGER_KEY} if case["should_trigger"] else set()
        pred = set(predictions[case["id"]])
        if suite == "trigger":
            pred &= {TRIGGER_KEY}
        if gold:
            flawed += 1
            if pred:
                detected += 1
        else:
            compliant += 1
            if pred:
                false_alarms += 1
        for item in items:
            g, p = item in gold, item in pred
            if p and g:
                per[item]["tp"] += 1
                tp += 1
            elif p and not g:
                per[item]["fp"] += 1
                fp += 1
            elif not p and g:
                per[item]["fn"] += 1
                fn += 1
            else:
                tn += 1
        if pred != gold:
            mismatches.append({
                "id": case["id"],
                "intent": case.get("intent", case.get("category", "")),
                "text": case["text"],
                "gold": sorted(gold), "pred": sorted(pred),
                "false_positive": sorted(pred - gold),
                "false_negative": sorted(gold - pred),
            })

    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "suite": suite, "source": source, "cases": len(cases),
        "flawed": flawed, "compliant": compliant,
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": prec, "precision_ci": wilson(tp, tp + fp),
        "recall": rec, "recall_ci": wilson(tp, tp + fn), "f1": f1,
        "detection": detected / flawed if flawed else float("nan"),
        "detection_ci": wilson(detected, flawed),
        "false_alarm_rate": false_alarms / compliant if compliant else float("nan"),
        "false_alarm_k": false_alarms,
        "per_check": per, "mismatches": mismatches,
    }


def to_markdown(results: dict[str, dict]) -> str:
    lines = [
        "# Extra eval suites",
        "",
        "> These tables score **deterministic baselines**, not model quality. "
        "The baselines are control groups. To score real model adjudication or "
        "real triggering, run with `--predictions`. No model score is invented here.",
        "",
        "| Suite | Source | Cases | Positive | Reverse | TP | FP | FN | Precision [95% CI] | Recall [95% CI] | F1 | Detection [95% CI] | False alarms |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for suite, r in results.items():
        lines.append(
            f"| {suite} | {r['source']} | {r['cases']} | {r['flawed']} | "
            f"{r['compliant']} | {r['TP']} | {r['FP']} | {r['FN']} | "
            f"{pct(r['precision'])} {interval(r['precision_ci'])} | "
            f"{pct(r['recall'])} {interval(r['recall_ci'])} | {r['f1']:.3f} | "
            f"{pct(r['detection'])} {interval(r['detection_ci'])} | "
            f"{pct(r['false_alarm_rate'])} ({r['false_alarm_k']}/{r['compliant']}) |"
        )
    sem = results.get("semantic")
    if sem:
        lines += ["", "## Semantic baseline per check", "",
                  "| Check | TP | FP | FN | Recall |", "|---|---|---|---|---|"]
        for cid in SEMANTIC_CHECKS:
            d = sem["per_check"][cid]
            rec = d["tp"] / (d["tp"] + d["fn"]) if d["tp"] + d["fn"] else float("nan")
            lines.append(f"| {cid} | {d['tp']} | {d['fp']} | {d['fn']} | {pct(rec)} |")
    lines += ["", "## Mismatches (kept, not patched away)", ""]
    for suite, r in results.items():
        for m in r["mismatches"]:
            lines.append(
                f"- `{suite}` `{m['id']}` ({m['intent']}) "
                f"FP={m['false_positive'] or '—'} FN={m['false_negative'] or '—'} "
                f"— {m['text']}"
            )
    lines += [
        "", "## What these numbers are NOT", "",
        "- They are not the model's semantic-adjudication accuracy. The "
        "baseline reads structured fields and never reads the claim text; "
        "four `hidden_contradiction` cases exist specifically to keep its "
        "recall below 1.00.",
        "- They are not trigger accuracy of any real agent harness. The "
        "trigger baseline is a handful of intent hints; two should-trigger "
        "cases have no hint and one should-not-trigger case contains hints.",
        "- Gold labels were written before running the baseline. Compliant "
        "traps (S18, S19, T20) intentionally produce false positives so the "
        "reverse test has teeth.",
        "- Sample sizes are 20 per suite; Wilson intervals are wide. Do not "
        "read a few points of difference as an improvement.",
        "", "## Reproduce", "",
        "```bash",
        "python scripts/eval_extras.py --self-test",
        "python scripts/eval_extras.py --suite all --out evals/EXTRAS_RESULTS.md",
        "python scripts/eval_extras.py --suite semantic --predictions model_semantic.json",
        "python scripts/eval_extras.py --suite trigger --predictions model_trigger.json",
        "```",
        "",
        "A `--predictions` file maps every case id to a list of check ids "
        "(semantic) or a boolean (trigger). Missing ids are rejected rather "
        "than silently treated as negatives.",
        "",
    ]
    return "\n".join(lines)


def self_test() -> None:
    sem = load_cases("semantic")
    tri = load_cases("trigger")
    by_id = {c["id"]: c for c in sem}

    assert "C02" in baseline_semantic(by_id["S01"]["material"]), "missed C02"
    assert baseline_semantic(by_id["S15"]["material"]) == set(), "false positive on clean case"
    assert baseline_trigger("帮我写一版 PRD，目标转化率 20%") is False, "PRD must not trigger"
    assert baseline_trigger("这个 94% 能写进周报吗？") is True, "audit must trigger"

    gold = {c["id"]: set(c["expected_semantic_checks"]) for c in sem}
    r = score("semantic", sem, gold, "self-test")
    assert r["precision"] == 1.0 and r["recall"] == 1.0, "scorer not self-consistent"

    try:
        normalize_predictions({"S01": []}, "semantic", sem)
        raise AssertionError("missing predictions must be rejected")
    except ValueError:
        pass

    assert math.isnan(wilson(0, 0)[0]), "n=0 must not produce an interval"
    json.dumps(score("trigger", tri, baseline_predictions("trigger", tri),
                     "self-test"), ensure_ascii=False)
    print("self-test: 7/7 passed")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", choices=("semantic", "trigger", "all"), default="all")
    ap.add_argument("--predictions", type=Path,
                    help="score external model output instead of the baseline")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    suites = ["semantic", "trigger"] if args.suite == "all" else [args.suite]
    results: dict[str, dict] = {}
    for suite in suites:
        cases = load_cases(suite)
        if args.predictions:
            preds = load_predictions(args.predictions, suite, cases)
            source = f"external ({args.predictions.name})"
        else:
            preds = baseline_predictions(suite, cases)
            source = "deterministic baseline"
        results[suite] = score(suite, cases, preds, source)

    output = (json.dumps(results, ensure_ascii=False, indent=2)
              if args.format == "json" else to_markdown(results))
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
