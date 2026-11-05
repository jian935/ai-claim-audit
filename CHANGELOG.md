# Changelog

All notable changes are documented here. Dates use ISO format. The repository is
<https://github.com/jian935/ai-claim-audit>.

## v1.0.0 — 2026-11-06

First public release.

### Shipped

- **One skill, one action**: `SKILL.md` turns an AI-product effect claim into a
  table of the exact questions that number cannot answer. It does not write a
  PRD and it does not design an eval plan.
- **12 checks (C01–C12)**: six deterministic pre-checks in the zero-dependency
  `scripts/audit_claims.py`, six model adjudications emitted as a mandatory
  checklist. Rubric, 11 failure patterns and the output format (with mandatory
  limitations) live in `references/`.
- **80 hand-labelled cases**: 24 dev + 16 hold-out machine-check claims,
  20 semantic-adjudication cases with structured material, 20 intent-labelled
  trigger messages. The main set contains 10 compliant reverse tests.
- **Three scorers** with Wilson 95% intervals; generated `evals/RESULTS.md` and
  `evals/EXTRAS_RESULTS.md` keep every mismatch instead of hiding it.
- **Blind-evaluation kit**: a label-free `evals/blind_pack.md`, an all-`null`
  `evals/predictions_template.json`, a `--predictions` scorer that refuses to
  run on unanswered cases, and `evals/BLIND_EVAL.md`.
- **CI regression gate**: regenerates five golden files on every push and PR;
  any diff fails the build. No hardcoded score thresholds.
- Bilingual READMEs with a number-symmetry lock, MIT licence, and an example
  built from a fabricated input with a genuinely generated report.

### Measured at this tag

| Suite | Cases | Headline |
|---|---|---|
| Machine-check claims (dev + hold-out) | 40 | claim detection **80.0%** [62.7, 90.5], micro-F1 **0.948**, **0/10** false alarms |
| Semantic baseline | 20 | F1 **0.800** |
| Trigger baseline | 20 | F1 **0.842** |

The two extra suites report **deterministic baselines, not model scores**. No
measured model-adjudication accuracy is published at this tag; the scorer is
ready but no model run has been recorded. Feeding gold labels back as
predictions returns 1.000 — that is a scorer self-check, not accuracy.

### Known limitations at this tag

- **8 documented rule-defect families**: F1–F3 in both READMEs, R1–R5 in
  `evals/README.md`. All were left frozen deliberately; each needs a new
  `holdout-v2.json` and a reverse test before it can ship.
- The same author wrote and saw both dev and hold-out labels, so this is
  **not a strictly independent hold-out**.
- The pre-check reads literal wording only; it never sees the dataset, labels,
  split or code. A clean pre-check is not evidence that a claim is true.
- CI runs Python 3.11 on ubuntu only.
- Small samples mean wide Wilson intervals; quote the intervals with the point
  estimates.

### Not included (planned, no dates)

A real blind-model score, a 30-second demo gif, and the v1.1 rule fixes. None
of these is required to install or use v1.0.0.
