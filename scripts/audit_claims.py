#!/usr/bin/env python3
"""Deterministic pre-check for AI-product effect claims.

Zero dependencies, Python 3.10+.

WHAT THIS IS
    A pre-check that raises *questions* about numbers in PRDs, weekly updates,
    launch reviews and READMEs. It never decides that a number is false, and it
    never invents a missing number.

WHAT THIS IS NOT
    Six of the twelve rubric checks (C02 C03 C04 C07 C08 C11) require reading
    the data and the measurement design. This script cannot do that. It emits
    them as a MANDATORY adjudication checklist for the model. Any report that
    skips that checklist is incomplete.

Usage:
    python scripts/audit_claims.py --input examples/bad_claims.md
    python scripts/audit_claims.py --input doc.md --format json --out report.json
    python scripts/audit_claims.py --text "准确率达到 94%，下周上线。"
    python scripts/audit_claims.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

CHECKS = {
    "C01": ("Denominator & sample size", "machine", "S2",
            "分母是什么？谁选的？换一个分母这个数会变成多少？"),
    "C02": ("Self-confirming target set", "semantic", "S1",
            "删掉正文里那个词，这条还会被选进目标集吗？"),
    "C03": ("Label provenance", "semantic", "S1",
            "这个标签是采集时留下的，还是有人针对这个问题重新标的？"),
    "C04": ("Hold-out and leakage", "semantic", "S1",
            "决定改法之前看过这批数据吗？有没有一块没动过的集合？"),
    "C05": ("Baseline / control", "machine", "S2",
            "跟什么比？两边是同一份数据、同一个口径吗？"),
    "C06": ("Uncertainty", "machine", "S2",
            "区间跨 0 吗？重跑一次会变多少？"),
    "C07": ("One definition, one source of truth", "semantic", "S1",
            "这个状态在别的报表里算正反馈吗？口径改过吗？"),
    "C08": ("Data artefacts before model quality", "semantic", "S1",
            "按正文去重了吗？样板文本是在入口剥掉的，还是靠改词表绕过去的？"),
    "C09": ("Synthetic data disclosure", "machine", "S3",
            "这是真实数据还是编的？为什么它跑出来这么好看？"),
    "C10": ("Reproducibility", "machine", "S3",
            "陌生人拿到仓库，能跑出同一个数吗？"),
    "C11": ("One-sided gain", "semantic", "S2",
            "哪个口径没涨？涨的那部分上限是多少？"),
    "C12": ("Correlation written as causation", "machine", "S2",
            "有没有对照组？还是只有一条相关系数？"),
}
MACHINE_CHECKS = tuple(k for k, v in CHECKS.items() if v[1] == "machine")
SEMANTIC_CHECKS = tuple(k for k, v in CHECKS.items() if v[1] == "semantic")
SEVERITY_ORDER = {"S3": 1, "S2": 2, "S1": 3}

# --- Triggers: structural number language, not domain vocabulary -----------
# Deliberately generic. A check must fire because a sentence makes a numeric
# claim without support, NOT because it contains a word from our eval set.
PCT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|％|个百分点|percent)|\b\d+\s*/\s*\d+\b", re.I)
RATE_WORD = re.compile(
    r"(?:准确率|精确率|召回率|完成率|通过率|命中率|转化率|覆盖率|占比|正确率|accuracy|precision|recall)", re.I)
DIGIT = re.compile(r"\d")

DENOM_EVIDENCE = re.compile(
    r"(?:分母|样本量|共\s*[\d,]+\s*[条个例人]|"
    r"\b[nN]\s*[=:]\s*[\d,]+|out\s+of\s+[\d,]+|"
    r"基于\s*[\d,]+\s*条|在\s*[\d,]+\s*条|"
    r"[\d,]+\s*条\s*(?:JD|样本|标注|记录|数据|评测|用例)|"
    r"[\d,]+\s*(?:labeled|labelled|samples?|rows?|cases?|JDs?|records?)|"
    r"\d[\d,]*\s*/\s*\d[\d,]*)", re.I)

LIFT = re.compile(
    r"(?:提升|提高|增长|上涨|下降|降低|减少|优化|翻倍|改善|"
    r"从\s*[\d.]+\s*%?\s*(?:到|至|→|~|-)\s*[\d.]+|"
    r"improved?|increased?|reduced?|decreased?|grew|lift(?:ed)?|"
    r"from\s+[\d.]+\s*(?:%|percent)?\s*to\s*[\d.]+)", re.I)
BASELINE_EVIDENCE = re.compile(
    r"(?:基线|对照组?|对照|旧版|上一版|改前|改动前|此前|同期|原方案|"
    r"相比|相较|A\s*/\s*B|AB\s*test|baseline|control\s*group|before|"
    r"previous\s*version|prior\s*version|compared\s*(?:with|to))", re.I)

CORR = re.compile(
    r"(?:相关系数|相关性|显著|\br\s*[=:]\s*-?\d|pearson|spearman|correlation|p\s*[<>]\s*0)", re.I)
UNCERTAINTY_EVIDENCE = re.compile(
    r"(?:置信区间|可信区间|区间|\bCI\b|标准误|方差|标准差|波动|重跑|重复跑|"
    r"seed|随机种子|\b[nN]\s*[=:]\s*[\d,]+|p\s*[<=]\s*0|p\s*value|"
    r"confidence\s*interval)", re.I)

SYNTH = re.compile(
    r"(?:示例|样例|演示|示意数据|demo|example\s*(?:data|output|table)|"
    r"sample\s*output|示例数据)", re.I)
SYNTH_DISCLOSURE = re.compile(
    r"(?:编造|虚构|示意|模拟数据|假设数据|非真实|mock|synthetic|fabricated|"
    r"illustrative|hypothetical|not\s+real|made[- ]up|for\s+demonstration)", re.I)

EVAL = re.compile(
    r"(?:实测|跑分|评测|评估(?:结果|集)?|实验(?:结果|数据)?|"
    r"准确率|精确率|召回率|正确率|\bF1\b|accuracy|precision|recall|"
    r"benchmark|eval(?:uation)?\s*(?:set|result|score))", re.I)
REPRO_EVIDENCE = re.compile(
    r"(?:复现|脚本|命令|数据版本|版本|commit|seed|随机种子|README|"
    r"仓库|\.py\b|python\s+-m|pip\s+install|可运行|reproduc|script|command|checksum)", re.I)

CAUSAL = re.compile(
    r"(?:带来|导致|使得|让|促成|拉动|归功于|led\s+to|drove|driven\s+by|"
    r"caused?|resulted\s+in|because\s+of)", re.I)
CAUSAL_HEDGE = re.compile(
    r"(?:相关|可能|似乎|未必|不确定|假设|associated|may|might|could|"
    r"cannot\s+prove|no\s+evidence)", re.I)

LIMITATIONS = (
    "This is a regex pre-check over the literal wording of a claim. It can "
    "detect a missing denominator, a missing comparator, a missing interval, "
    "an undisclosed demo, a missing reproduction pointer, and causal verbs. "
    "It CANNOT see the dataset, the label source, the train/test split, the "
    "metric definition in code, or duplicated rows. Six semantic checks are "
    "listed for mandatory model adjudication and are not auto-scored. A clean "
    "pre-check is not evidence that a claim is true."
)


def split_claims(text: str) -> list[str]:
    """Split a document into single-claim strings.

    Headings, fenced code, separator rows and short cells are dropped. Chinese
    JDs and updates often put several claims on one line, so split on sentence
    enders and semicolons as well as newlines.
    """
    out: list[str] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line or line.startswith("#") or line.startswith(">"):
            continue
        if re.fullmatch(r"[|:\-\s]+", line):
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            out.extend(c for c in cells if len(c) >= 8 and DIGIT.search(c))
            continue
        line = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", line)
        for part in re.split(r"(?<=[。！？!?])\s*|(?<=\.)\s+(?=[A-Z])|;|；", line):
            part = part.strip()
            if len(part) >= 6:
                out.append(part)
    return out


def precheck_claim(text: str) -> list[str]:
    """Return the machine-check IDs whose supporting evidence is absent."""
    raised: list[str] = []
    has_number = bool(DIGIT.search(text))

    if (PCT.search(text) or (RATE_WORD.search(text) and has_number)) \
            and not DENOM_EVIDENCE.search(text):
        raised.append("C01")
    if LIFT.search(text) and not BASELINE_EVIDENCE.search(text):
        raised.append("C05")
    if CORR.search(text) and not UNCERTAINTY_EVIDENCE.search(text):
        raised.append("C06")
    if SYNTH.search(text) and not SYNTH_DISCLOSURE.search(text):
        raised.append("C09")
    if EVAL.search(text) and has_number and not REPRO_EVIDENCE.search(text):
        raised.append("C10")
    if CAUSAL.search(text) and has_number and not CAUSAL_HEDGE.search(text):
        raised.append("C12")
    return raised


def precheck(text: str) -> dict:
    """Build the full pre-check result for a document."""
    claims = []
    for i, sentence in enumerate(split_claims(text), 1):
        raised = precheck_claim(sentence)
        severity = "—"
        if raised:
            severity = max((CHECKS[c][2] for c in raised),
                           key=lambda s: SEVERITY_ORDER[s])
        claims.append({
            "id": f"Q{i:02d}",
            "text": sentence,
            "raised": raised,
            "severity": severity,
            "questions": [CHECKS[c][3] for c in raised],
        })
    return {
        "version": VERSION,
        "machine_checks": list(MACHINE_CHECKS),
        "semantic_checks": list(SEMANTIC_CHECKS),
        "claims": claims,
        "summary": {
            "claims_scanned": len(claims),
            "claims_with_raised_checks": sum(1 for c in claims if c["raised"]),
            "raised_total": sum(len(c["raised"]) for c in claims),
        },
        "limitations": LIMITATIONS,
    }


def to_markdown(result: dict) -> str:
    lines = [
        "# AI Claim Audit — deterministic pre-check",
        "",
        "> A raised check is a **question**, not a verdict. Semantic checks are "
        "not scored by this script; see the mandatory checklist below.",
        "",
        f"Scanned {result['summary']['claims_scanned']} claim(s); "
        f"{result['summary']['claims_with_raised_checks']} raised at least one "
        f"question; {result['summary']['raised_total']} question(s) total.",
        "",
        "| # | Claim | Raised | Sev | Question to answer |",
        "|---|---|---|---|---|",
    ]
    for c in result["claims"]:
        cell = c["text"].replace("|", "\\|")
        raised = ", ".join(c["raised"]) or "—"
        q = " / ".join(c["questions"]) or "—"
        lines.append(f"| {c['id']} | {cell} | {raised} | {c['severity']} | {q} |")
    lines += [
        "",
        "## Mandatory model adjudication checklist",
        "",
        "For **every** claim above, decide these six checks using "
        "`references/audit-rubric.md` and `references/failure-patterns.md`:",
        "",
    ]
    for cid in SEMANTIC_CHECKS:
        name, _, sev, question = CHECKS[cid]
        lines.append(f"- **{cid} {name}** ({sev}) — {question}")
    lines += [
        "",
        "Do not conclude from the machine-raised rows alone. Do not invent "
        "missing numbers. A rewritten claim must be weaker than or equal to "
        "the original.",
        "",
        "## Limitations of this audit",
        "",
        result["limitations"],
        "",
        f"_ai-claim-audit v{result['version']} · MIT · jian935_",
        "",
    ]
    return "\n".join(lines)


def self_test() -> None:
    bad = "效果很好，准确率达到 94%，下周上线。"
    r = precheck_claim(bad)
    assert {"C01", "C10"} <= set(r), f"missed denominator/reproduction pointer: {r}"

    good = ("在 1,167 条 JD 的留出集上，规则引擎的岗位族识别准确率为 93.6%，"
            "n=1167，复现脚本 scripts/real_eval_family.py，数据版本 2026-10-28。")
    assert precheck_claim(good) == [], f"false positive on a compliant claim: {precheck_claim(good)}"

    lift = "新版本让任务完成率从 62% 提升到 89%。"
    r2 = precheck_claim(lift)
    assert "C05" in r2 and "C12" in r2, f"missed baseline/causation: {r2}"

    corr = "匹配分与实际回复的相关系数 r=0.62。"
    assert "C06" in precheck_claim(corr), "missed missing interval"

    demo = "示例数据里 10 条全部通过，效果稳定。"
    assert "C09" in precheck_claim(demo), "missed undisclosed demo data"

    two = split_claims("准确率 94%。成本下降 30%。")
    assert len(two) == 2, f"inline sentence splitting failed: {two}"

    eng = split_claims("Accuracy 94%. Cost dropped 30%.")
    assert len(eng) == 2, f"english sentence splitting failed: {eng}"

    json.dumps(precheck(bad + "\n" + good), ensure_ascii=False)
    print("self-test: 7/7 passed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, help="path to a .md/.txt document")
    ap.add_argument("--text", help="inline claim text instead of a file")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--out", type=Path, help="write report to this path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.input and not args.text:
        ap.error("provide --input, --text, or --self-test")

    if args.input and not args.input.exists():
        ap.error(f"input file not found: {args.input}")
    try:
        text = args.input.read_text(encoding="utf-8") if args.input else args.text
    except OSError as exc:
        ap.error(f"cannot read {args.input}: {exc}")
    result = precheck(text)
    output = (json.dumps(result, ensure_ascii=False, indent=2)
              if args.format == "json" else to_markdown(result))
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
