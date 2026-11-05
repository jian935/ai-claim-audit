# Eval set design and known limits

Run it:

```bash
python scripts/run_evals.py --split all --out evals/RESULTS.md
python scripts/audit_claims.py --self-test
```

40 hand-labelled claims: 24 dev / 16 hold-out, 30 flawed / 10 compliant.
`RESULTS.md` is generated, not hand-edited.

## How the target set is defined

**By claim type, never by keyword.** Every case carries a `category`
(`accuracy_claim`, `lift_claim`, `correlation_claim`, `eval_design_claim`,
`synthetic_claim`, `reproducibility_claim`, `causal_claim`, `cost_claim`,
`compliant`). A case belongs to the flawed set because a careful reviewer
judges that the sentence fails to supply evidence — not because the sentence
contains a word the script happens to look for.

This matters because this skill exists to catch self-confirming eval sets.
If its own eval set were "claims whose text contains the trigger regex", the
score would be 1.00 by construction and would prove nothing. Cases `D15`,
`D16`, `D17` and `H11` are the guard: they are genuinely broken claims whose
machine gold label is **empty**. The pre-check is silent on all four, and they
count as misses in claim-level detection. That 20% gap is reported, not hidden.

## Labelling discipline

- Gold labels are human judgements of **what evidence the sentence supplies**.
  They were not derived from the script's output.
- When a label and the engine disagree, first decide which is wrong. Fix the
  label if the label is wrong; do not bend the engine to agree with a bad
  label. D12 is a case where the label is right and the engine is wrong, so
  the false positive is kept.
- Compliant cases are the reverse test: a sentence that supplies the evidence
  must not be flagged. 10 of them, 0 false alarms.
- No missing number is invented to make a case pass.

## Dev / hold-out discipline

1. `dev.json` (24 cases) was written first and used to design the six regex
   rules. dev result: TP=28 FP=1 FN=1, claim detection 77.8%.
2. `scripts/audit_claims.py` was then **frozen**. No rule was edited while
   writing `holdout.json` (16 cases, deliberately different wording).
3. hold-out result: TP=18 FP=2 FN=1, claim detection 83.3%. precision drops
   from 96.6% to 90.0% — the hold-out did its job.

**Honest caveat:** the same author wrote both files and saw both, so this is
NOT a strictly independent hold-out. It is a weak check against phrasing
overfitting, not a guarantee of generalisation. Wilson intervals are wide at
these sample sizes; do not read a few points of difference as an improvement.

## What is NOT scored

Six of the twelve rubric checks (`C02 C03 C04 C07 C08 C11`) require reading the
dataset, the label source, the split, or the metric definition in code. They
are **not auto-scored**. The script emits them as a mandatory adjudication
checklist. No claim is made here about the model's adjudication quality; a
separate human-graded rubric would be needed for that.

A clean pre-check is not evidence that a claim is true.

## Known systematic failures (v1.0.0, intentionally left in)

Kept visible because fixing a regex on the same cases used to measure it is
how a benchmark quietly becomes self-confirming. Each is scheduled for v1.1
**with a reverse test that asserts the compliant cases still pass**.

| # | Family | Cases | Effect |
|---|---|---|---|
| F1 | Chinese quantity phrases with an inserted modifier — `45 条真实 JD`, `50 条人工标注` — are not recognised as denominators. | D12, H07 | 2 false positives on C01 |
| F2 | A rate word and an unrelated number in the same sentence — `显著提升了转化率，r=0.58` — triggers C01 even though 0.58 is a coefficient. | H06 | 1 false positive on C01 |
| F3 | Chinese multipliers with no Arabic numeral — `多跑三倍`, `砍掉一半` — are not recognised as lift claims. | D18, H12 | 2 false negatives on C05 (recall 81.8%) |

Planned reverse tests for v1.1:

- F1: widening the denominator pattern must leave `G01 G03 H13 H14` unflagged.
- F2: requiring the rate word to be adjacent to its own number must leave
  `G02 H15` (coefficients with intervals) unflagged.
- F3: adding Chinese numeral multipliers must leave `G04 G05 H16`
  (disclosed demo data) unflagged.

Do not change a rule to chase a single failing case before simulating how many
misses the change can actually recover. If the ceiling is zero, stop.

## Adding a case

Add to `dev.json` only while rules are still being designed, or to a new
`holdout-v2.json` after the next freeze. Every new flawed case needs a
`category`, a human-written reason in `note`, and — if it is a compliant case —
`expected_machine_checks: []`. Never define a new case as "text containing X".
