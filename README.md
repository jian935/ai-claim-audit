# ai-claim-audit

**Point it at any AI-product sentence with a number in it. Get a table of the exact questions that number cannot answer.**

[![CI](https://github.com/jian935/ai-claim-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/jian935/ai-claim-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
![Zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)
![Agent Skill](https://img.shields.io/badge/Claude%20Code-Skill-9555CC.svg)
![Labelled claims](https://img.shields.io/badge/labelled%20claims-80-informational.svg)

> On **40 hand-labelled machine-check claims**, the deterministic pre-check reaches **80.0% claim detection** (95% CI 62.7–90.5), **micro-F1 0.948**, and **0/10 false alarms** on compliant claims. The other 20% are semantic flaws a regex cannot see — that gap is the whole reason this skill exists. Full numbers, intervals and every kept mismatch: [`evals/RESULTS.md`](evals/RESULTS.md).
>
> Two more suites cover the other two gaps: **20 semantic-adjudication cases** (baseline **F1 0.800**) and **20 trigger-precision cases** (baseline **F1 0.842**). These are control-group baselines, **not model scores**; real model output is scored with `--predictions`. See [`evals/EXTRAS_RESULTS.md`](evals/EXTRAS_RESULTS.md).

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
| Almost all of the above are pure Markdown prompt templates | Ships a runnable zero-dependency script, 80 labelled cases, three scorers, and generated results tables |

The gap is narrow on purpose: **nobody was auditing the numbers that come out of those workflows.** A single skill, one action, one sentence to describe it.

Trigger-precision has a few tiny general-purpose checkers (four repositories, max 2 stars, surveyed 2026-11-05), but none is a labelled suite for this vertical. Metric-contract / definition-drift tools do exist (`jigonyoo/metrics-contract`, `vermapragya/open-metric-contracts`); this repo audits claim text, not dashboard SQL.

## How this avoids auditing itself into a tautology

A skill that catches self-confirming measurements must not be measured that way.

1. **The target set is defined by claim type, not by keyword.** Cases are grouped as `accuracy_claim`, `lift_claim`, `correlation_claim`, … A case is flawed because a human judges the sentence fails to supply evidence — not because its text contains a trigger regex.
2. **Gold labels are human judgements, not script output.** When a label and the engine disagree, decide which is wrong first. `D12` is a case where the label is right and the engine is wrong, so the false positive stays.
3. **Four deliberately invisible cases.** `D15`–`D17` and `H11` are genuinely broken claims (circular target set, crawler keyword as label, mixed metric definition) whose machine gold label is **empty**. The pre-check is silent on all four, and they count as misses in claim-level detection.
4. **Freeze before hold-out.** Rules were designed on `dev.json` (24 cases, detection 77.8%, F1 0.966), then `scripts/audit_claims.py` was frozen. `holdout.json` (16 cases, different wording) was written afterwards: precision fell from **96.6% → 90.0%**. That drop is reported, not patched away.
5. **Mismatches are kept.** 3 false positives and 2 false negatives remain in `RESULTS.md`, with the three systematic families explained in [`evals/README.md`](evals/README.md). 10 compliant claims serve as reverse tests (0 false alarms).
6. **The extra suites have traps too.** `S18`, `S19`, `T20` are compliant cases designed to make a shallow baseline fail; `S11`–`S14`, `T06`, `T09` are positive cases designed to be missed.

Honest caveat: the same author wrote both splits and saw both, so this is **not a strictly independent hold-out**. It is a weak guard against phrasing overfitting, nothing more.

## Eval results

```bash
python scripts/audit_claims.py --self-test     # 7/7
python scripts/eval_extras.py --self-test      # 7/7
python scripts/run_evals.py --split all --out evals/RESULTS.md
python scripts/eval_extras.py --suite all --out evals/EXTRAS_RESULTS.md
python scripts/check_docs.py
```

| Split | Cases | Flawed | Compliant | TP | FP | FN | Precision [95% CI] | Recall [95% CI] | F1 | Claim detection [95% CI] | False alarms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 24 | 18 | 6 | 28 | 1 | 1 | 96.6% [82.8, 99.4] | 96.6% [82.8, 99.4] | 0.966 | 77.8% [54.8, 91.0] | 0/6 |
| holdout | 16 | 12 | 4 | 18 | 2 | 1 | 90.0% [69.9, 97.2] | 94.7% [75.4, 99.1] | 0.923 | 83.3% [55.2, 95.3] | 0/4 |
| **all** | **40** | **30** | **10** | **46** | **3** | **2** | **93.9% [83.5, 97.9]** | **95.8% [86.0, 98.8]** | **0.948** | **80.0% [62.7, 90.5]** | **0/10** |

Claim detection is deliberately lower than the micro metrics: semantic-only flaws have an empty machine gold label, so a correct-but-silent pre-check counts as a miss.

## Two more eval suites

The main table covers only the six deterministic checks. Two more suites close the other two gaps in skill quality: semantic adjudication and trigger precision. Both are labelled by intent/type, never by keyword presence — `T11`/`T13`/`T15` contain numbers but must not trigger, while `T02`/`T08` contain no number but must trigger.

| Suite | Cases | Precision [95% CI] | Recall [95% CI] | F1 | Detection [95% CI] | False alarms |
|---|---|---|---|---|---|---|
| semantic baseline | 20 | 85.7% [60.1, 96.0] | 75.0% [50.5, 89.8] | **0.800** | 71.4% [45.4, 88.3] | 2/6 |
| trigger baseline | 20 | 88.9% [56.5, 98.0] | 80.0% [49.0, 94.3] | **0.842** | 80.0% [49.0, 94.3] | 1/10 |

**These are baselines, not model quality.** The semantic baseline reads structured `material` fields and never reads the claim text; four `hidden_contradiction` cases (`S11`–`S14`) exist to keep its recall at 75.0%. The trigger baseline is a handful of intent hints; two should-trigger messages contain no hint and one should-not-trigger message contains two. Compliant traps (`S18`, `S19`, `T20`) deliberately produce false positives.

To score real model output:

```bash
python scripts/eval_extras.py --suite semantic --predictions model_semantic.json
python scripts/eval_extras.py --suite trigger --predictions model_trigger.json
```

The scorer accepts a JSON map of case id → list of check ids / boolean, rejects missing ids, and reports the same table with Wilson intervals. **This repo does not fabricate that score.** Feeding the gold labels back as predictions returns 1.000 — that is a scorer self-check, not an accuracy claim.

CI regenerates every report and fails the PR if any golden file changes: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Known limitations

| Family | Effect | v1.1 plan |
|---|---|---|
| Chinese quantity phrases with an inserted modifier (`45 条真实 JD`) | 2 false positives on C01 | Widen denominator pattern + reverse test on `G01 G03 H13 H14` |
| A rate word and an unrelated number in one sentence (`转化率…r=0.58`) | 1 false positive on C01 | Require adjacency + reverse test on `G02 H15` |
| Chinese multipliers without Arabic numerals (`多跑三倍`, `砍掉一半`) | 2 false negatives on C05 (recall 81.8%) | Add numeral multipliers + reverse test on `G04 G05 H16` |

Also: small samples mean wide Wilson intervals; the pre-check sees only literal wording, not your dataset, labels, split or code; and a clean pre-check is **not** evidence that a claim is true. The two extra suites ship baselines and a scorer, **not** measured model-adjudication accuracy or measured trigger accuracy of a real agent harness — both need a `--predictions` run before any such number can be quoted. The CI badge goes live after the first push to GitHub.

## Layout

```
SKILL.md                       skill entry point and workflow
scripts/audit_claims.py        zero-dependency pre-check, md/json, --self-test
scripts/run_evals.py           dev/hold-out scorer with Wilson intervals
scripts/eval_extras.py         semantic + trigger baselines, --predictions scorer
scripts/check_docs.py          bilingual README number lock
references/audit-rubric.md     12 checks, passing evidence, severity
references/failure-patterns.md 11 real traps and diagnosis order
references/output-format.md    report template + mandatory limitations
evals/dev.json                 24 labelled claims (rule design)
evals/holdout.json             16 labelled claims (written after freeze)
evals/semantic.json            20 cases with structured material + human gold
evals/trigger.json             20 intent-labelled user messages
evals/RESULTS.md               generated main scores and kept mismatches
evals/EXTRAS_RESULTS.md        generated baseline scores for the two extra suites
evals/README.md                eval design, labelling discipline, known failures
examples/                      fabricated input + a really generated report
.github/workflows/ci.yml       regeneration + diff regression gate
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version: new cases need a claim-type category and a human reason; every rule change needs a reverse test; never define a target set by keyword presence.

MIT © 2026 jian935
