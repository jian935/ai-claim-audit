# ai-claim-audit

**Point it at any AI-product sentence with a number in it. Get a table of the exact questions that number cannot answer.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
![Zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)
![Agent Skill](https://img.shields.io/badge/Claude%20Code-Skill-9555CC.svg)
![Labelled claims](https://img.shields.io/badge/labelled%20claims-40-informational.svg)

> On **40 hand-labelled claims**, the deterministic pre-check reaches **80.0% claim detection** (95% CI 62.7–90.5), **micro-F1 0.948**, and **0/10 false alarms** on compliant claims. The other 20% are semantic flaws a regex cannot see — that gap is the whole reason this skill exists. Full numbers, intervals and every kept mismatch: [`evals/RESULTS.md`](evals/RESULTS.md).

A Claude Code / Agent Skill for AI product managers. It does not write your PRD and it does not design your eval plan. It reads the numbers you already wrote and asks: *what would I need to see to believe this?*

---

## 30-second demo

```bash
python scripts/audit_claims.py --text "模型准确率达到 94%，下周上线。"
```

```
| # | Claim | Raised | Sev | Question to answer |
| Q01 | 模型准确率达到 94%，下周上线。 | C01, C10 | S2 | 分母是什么？... / 陌生人拿到仓库，能跑出同一个数吗？ |
```

Then the skill adjudicates six semantic checks the script cannot score, and writes a full [`examples/audit_report.md`](examples/audit_report.md). Note what that generated report shows: `Q06` is a **self-confirming target set** that supplies every machine-visible piece of evidence, so the pre-check is completely silent on it; `Q07` is a compliant claim that is correctly left alone. Both are intentional.

## Install

```bash
npx skills add jian935/ai-claim-audit
# or
git clone https://github.com/jian935/ai-claim-audit.git ~/.claude/skills/ai-claim-audit
```

Then paste a claim, a PRD section, or a whole weekly update into the chat. The skill triggers on "can I quote this number", "review this launch report", "帮我看看这份评测报告", and similar.

## What it checks

| ID | Check | Scored by | Severity |
|---|---|---|---|
| C01 | Denominator & sample size | script | S2 |
| C02 | Self-confirming target set | model | **S1** |
| C03 | Label provenance | model | **S1** |
| C04 | Hold-out and leakage | model | **S1** |
| C05 | Baseline / control | script | S2 |
| C06 | Uncertainty (`n`, interval, run variance) | script | S2 |
| C07 | One metric definition, one source of truth | model | **S1** |
| C08 | Data artefacts before model quality | model | **S1** |
| C09 | Synthetic data disclosure | script | S3 |
| C10 | Reproducibility | script | S3 |
| C11 | One-sided gain | model | S2 |
| C12 | Correlation written as causation | script | S2 |

A raised check is a **question**, never an accusation. The skill does not verify whether a number is true; it verifies whether the stated evidence supports it. Rewrites are always weaker than the original.

## Why this is not another PM skill pack

Surveyed on GitHub, 2026-11-05:

| Already crowded | This repo |
|---|---|
| PRD / roadmap / RICE / JTBD / competitive analysis packs, including a 70-skill collection and a 466-skill multi-profession catalogue | Does not generate any document |
| An AI-PM judgement skill covering rules→RAG→agent selection, falsifying POCs, eval layers and launch gates | Does not decide what to build |
| At least four `ai-eval-plan` / `eval-framework-builder` style skills | Does not design an eval plan |
| Almost all of the above are pure Markdown prompt templates | Ships a runnable zero-dependency script, 40 labelled cases, a scorer, and a generated results table |

The gap is narrow on purpose: **nobody was auditing the numbers that come out of those workflows.** A single skill, one action, one sentence to describe it.

## How this avoids auditing itself into a tautology

A skill that catches self-confirming measurements must not be measured that way.

1. **The target set is defined by claim type, not by keyword.** Cases are grouped as `accuracy_claim`, `lift_claim`, `correlation_claim`, … A case is flawed because a human judges the sentence fails to supply evidence — not because its text contains a trigger regex.
2. **Gold labels are human judgements, not script output.** When a label and the engine disagree, decide which is wrong first. `D12` is a case where the label is right and the engine is wrong, so the false positive stays.
3. **Four deliberately invisible cases.** `D15`–`D17` and `H11` are genuinely broken claims (circular target set, crawler keyword as label, mixed metric definition) whose machine gold label is **empty**. The pre-check is silent on all four, and they count as misses in claim-level detection.
4. **Freeze before hold-out.** Rules were designed on `dev.json` (24 cases, detection 77.8%, F1 0.966), then `scripts/audit_claims.py` was frozen. `holdout.json` (16 cases, different wording) was written afterwards: precision fell from **96.6% → 90.0%**. That drop is reported, not patched away.
5. **Mismatches are kept.** 3 false positives and 2 false negatives remain in `RESULTS.md`, with the three systematic families explained in [`evals/README.md`](evals/README.md). 10 compliant claims serve as reverse tests (0 false alarms).

Honest caveat: the same author wrote both splits and saw both, so this is **not a strictly independent hold-out**. It is a weak guard against phrasing overfitting, nothing more.

## Eval results

```bash
python scripts/audit_claims.py --self-test     # 6/6
python scripts/run_evals.py --split all --out evals/RESULTS.md
```

| Split | Cases | Flawed | Compliant | TP | FP | FN | Precision [95% CI] | Recall [95% CI] | F1 | Claim detection [95% CI] | False alarms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 24 | 18 | 6 | 28 | 1 | 1 | 96.6% [82.8, 99.4] | 96.6% [82.8, 99.4] | 0.966 | 77.8% [54.8, 91.0] | 0/6 |
| holdout | 16 | 12 | 4 | 18 | 2 | 1 | 90.0% [69.9, 97.2] | 94.7% [75.4, 99.1] | 0.923 | 83.3% [55.2, 95.3] | 0/4 |
| **all** | **40** | **30** | **10** | **46** | **3** | **2** | **93.9% [83.5, 97.9]** | **95.8% [86.0, 98.8]** | **0.948** | **80.0% [62.7, 90.5]** | **0/10** |

Claim detection is deliberately lower than the micro metrics: semantic-only flaws have an empty machine gold label, so a correct-but-silent pre-check counts as a miss. The six semantic checks are **not auto-scored** — no claim is made about model adjudication quality.

## Known limitations

| Family | Effect | v1.1 plan |
|---|---|---|
| Chinese quantity phrases with an inserted modifier (`45 条真实 JD`) | 2 false positives on C01 | Widen denominator pattern + reverse test on `G01 G03 H13 H14` |
| A rate word and an unrelated number in one sentence (`转化率…r=0.58`) | 1 false positive on C01 | Require adjacency + reverse test on `G02 H15` |
| Chinese multipliers without Arabic numerals (`多跑三倍`, `砍掉一半`) | 2 false negatives on C05 (recall 81.8%) | Add numeral multipliers + reverse test on `G04 G05 H16` |

Also: small samples mean wide Wilson intervals; the pre-check sees only literal wording, not your dataset, labels, split or code; and a clean pre-check is **not** evidence that a claim is true.

## Layout

```
SKILL.md                     skill entry point and workflow
scripts/audit_claims.py      zero-dependency pre-check, md/json, --self-test
scripts/run_evals.py         dev/hold-out scorer with Wilson intervals
references/audit-rubric.md   12 checks, passing evidence, severity
references/failure-patterns.md  11 real traps and diagnosis order
references/output-format.md  report template + mandatory limitations
evals/dev.json               24 labelled claims (rule design)
evals/holdout.json           16 labelled claims (written after freeze)
evals/RESULTS.md             generated scores and kept mismatches
evals/README.md              eval design, labelling discipline, known failures
examples/                    fabricated input + a really generated report
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version: new cases need a claim-type category and a human reason; every rule change needs a reverse test; never define a target set by keyword presence.

MIT © 2026 jian935
