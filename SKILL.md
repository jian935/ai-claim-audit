---
name: ai-claim-audit
description: Audit effect and quality claims in AI product writing — PRDs, weekly updates, launch reviews, experiment reports, READMEs and portfolio write-ups — for numbers that cannot be trusted. Detect missing denominators and baselines, self-confirming eval sets, collection-time labels used as ground truth, missing hold-outs, mixed metric definitions, undisclosed demo data, correlation written as causation, and results nobody can reproduce. Produce a per-claim audit table with severity, the exact evidence to request, and a weaker rewrite. This skill should be used when a user pastes a claim like "accuracy improved from 62% to 94%", asks to review an AI feature's metrics, PRD, launch report or eval design, or asks whether a reported improvement can be trusted; also trigger on "这个数字能写进周报吗" and "帮我看看这份评测报告".
---

# AI Claim Audit

## Purpose

Turn a paragraph of confident AI-product numbers into a table of concrete,
answerable questions. Most bad metrics are not lies — they are numbers whose
denominator, label source, split, baseline or metric definition was never
stated. This skill finds those omissions without accusing anyone, and rewrites
the claim so it says only what the evidence supports.

Twelve checks exist. Six have a deterministic pre-check; six require reading
the measurement design. **Never conclude from the pre-check alone.**

## When to use

- Review a PRD, weekly update, launch review, experiment report, README or
  portfolio write-up that quotes an accuracy, lift, correlation, cost or
  conversion number.
- Decide whether a number can be quoted externally.
- Diagnose a metric that looks too good (`100%`, `1.00`) or implausibly bad.
- Compare two reports whose numbers for "the same" metric disagree.

## When not to use

- Writing a PRD or designing an eval plan from scratch (use a PRD / eval-plan
  skill instead).
- Verifying whether a number is factually true. This skill verifies whether the
  number is *supported by stated evidence*; it has no access to the dataset.
- Reviewing code that contains no effect claims.

## Workflow

### 1. Extract claims

Split the input into single-claim sentences. Chinese product docs commonly put
several claims on one line — split on `。！？;` and `；` as well as newlines.
Drop headings, code fences and table separators. Keep table cells that contain
a number. Quote the original fragment verbatim in the report; paraphrasing
hides the problem.

### 2. Run the deterministic pre-check

```bash
python scripts/audit_claims.py --input <doc.md> --format json
python scripts/audit_claims.py --text "准确率达到 94%，下周上线。"
python scripts/audit_claims.py --self-test
```

The script raises questions for six checks (`C01` denominator, `C05` baseline,
`C06` uncertainty, `C09` synthetic disclosure, `C10` reproducibility, `C12`
causation) and emits the other six as a **mandatory adjudication checklist**.
It scores nothing about the six semantic checks. Run `--self-test` after
editing any rule.

### 3. Load the rubric and the failure library

Read `references/audit-rubric.md` for the twelve definitions, passing evidence,
and severity. Read `references/failure-patterns.md` when a claim looks plausible
but something feels off — it records the fixes that actually worked, because
the obvious fix (adding keywords, retraining, swapping the scorer) is usually
the wrong one. Follow its diagnosis order: artefacts → definitions → labels →
target set → split → baseline → uncertainty → denominator → slices → causation.

### 4. Adjudicate all twelve checks for every claim

Decide `C02` (self-confirming target set), `C03` (label provenance), `C04`
(hold-out), `C07` (one metric definition), `C08` (data artefacts) and `C11`
(one-sided gain) explicitly for **each** claim, including claims the pre-check
left clean. Where the user has not supplied the material needed to judge,
write `无法判断 / cannot determine` — never `通过 / pass`.

Four cases in this repo's eval set (`D15`–`D17`, `H11`) are broken claims on
which the pre-check is completely silent. A clean pre-check proves nothing.

### 5. Write the report

Use `references/output-format.md`: one table, one requested-input list, one
weaker rewrite, and a mandatory limitations section. Include compliant claims
as rows with `命中检查 = —` so the reader can verify the same standard was
applied to good and bad claims.

## Hard rules

- Treat a raised check as a question, never as proof of fabrication.
- Never invent a missing number. Name the missing artifact and request it.
- Diagnose data artefacts and metric definitions before model quality.
- Count each problem once. Assign the highest severity among raised checks
  (`S1 > S2 > S3`); never average or add severities.
- Rewrite claims weaker than or equal to the original. Never strengthen a
  claim while "fixing" it.
- Give every `S1` a rebuild instruction, not a caveat. A self-confirming
  target set cannot be rescued by a footnote.
- Close every report with the limitations of the audit itself.
- Do not edit a regex to make a single eval case pass. Widen a rule only on the
  dev split, then add a reverse test asserting the compliant cases still pass.

## Resources

| Path | Use |
|---|---|
| `scripts/audit_claims.py` | Zero-dependency deterministic pre-check, Markdown/JSON output, `--self-test` |
| `scripts/run_evals.py` | Score the pre-check on dev/hold-out, Wilson 95% intervals |
| `references/audit-rubric.md` | Twelve checks, passing evidence, severity, adjudication rules |
| `references/failure-patterns.md` | Eleven real failure patterns and the diagnosis order |
| `references/output-format.md` | Report template and the mandatory limitations section |
| `evals/dev.json`, `evals/holdout.json` | 40 hand-labelled claims, 10 compliant reverse tests |
| `evals/RESULTS.md` | Generated scores, kept mismatches, known systematic failures |
| `examples/` | A fabricated input document and a real generated report |

## Quick example

Input:

> 模型准确率达到 94%，下周上线。

Pre-check raises `C01` (no denominator) and `C10` (no reproduction pointer).
The model then adjudicates the semantic checks, marks `C02`/`C03`/`C04` as
`cannot determine` because no eval design was supplied, and returns:

| Claim | Checks | Sev | Missing | To request |
|---|---|---|---|---|
| 「模型准确率达到 94%」 | C01, C10 | S2 | 评测集条数与正例定义、跑分脚本、数据版本 | `n`、目标集构造规则、复现命令 |

Rewrite: 「在 <待补：n 条、来源、口径> 上测得 94%；尚不能推广到线上流量。」

The number is not called false. It is called unsupported, which is the only
claim this skill can actually make.
