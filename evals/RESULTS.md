# Eval results — deterministic pre-check only

> Scores cover the six machine checks (C01 C05 C06 C09 C10 C12). The six semantic checks are NOT auto-scored. A clean pre-check is not evidence that a claim is true.

| Split | Cases | Flawed | Compliant | TP | FP | FN | Precision [95% CI] | Recall [95% CI] | F1 | Claim detection [95% CI] | False-alarm rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 24 | 18 | 6 | 28 | 1 | 1 | 96.6% [82.8, 99.4] | 96.6% [82.8, 99.4] | 0.966 | 77.8% [54.8, 91.0] | 0.0% (0/6) |
| holdout | 16 | 12 | 4 | 18 | 2 | 1 | 90.0% [69.9, 97.2] | 94.7% [75.4, 99.1] | 0.923 | 83.3% [55.2, 95.3] | 0.0% (0/4) |
| all | 40 | 30 | 10 | 46 | 3 | 2 | 93.9% [83.5, 97.9] | 95.8% [86.0, 98.8] | 0.948 | 80.0% [62.7, 90.5] | 0.0% (0/10) |

**Claim detection** = share of flawed claims where the pre-check raised at least one question. It is deliberately lower than the micro metrics: semantic-only flaws (self-confirming target sets, bad labels, mixed definitions) have an empty machine gold label, so a correct-but-silent pre-check counts as a miss. That gap is the point of this table.

- dev: 3 semantic-only flawed claim(s), 0 raised any machine question — these require model adjudication.
- holdout: 1 semantic-only flawed claim(s), 0 raised any machine question — these require model adjudication.
- all: 4 semantic-only flawed claim(s), 0 raised any machine question — these require model adjudication.

## Per-check breakdown

| Check | Name | TP | FP | FN | Recall |
|---|---|---|---|---|---|
| C01 | Denominator & sample size | 14 | 3 | 0 | 100.0% |
| C05 | Baseline / control | 9 | 0 | 2 | 81.8% |
| C06 | Uncertainty | 4 | 0 | 0 | 100.0% |
| C09 | Synthetic data disclosure | 4 | 0 | 0 | 100.0% |
| C10 | Reproducibility | 11 | 0 | 0 | 100.0% |
| C12 | Correlation written as causation | 4 | 0 | 0 | 100.0% |

## Mismatches (kept, not patched away)

- `dev` `D12` (accuracy_claim) FP=['C01'] FN=— — 人工标注 45 条真实 JD，族识别准确率 100%。
- `dev` `D18` (cost_claim) FP=— FN=['C05'] — 同样预算下能多跑三倍请求。
- `holdout` `H06` (correlation_claim) FP=['C01'] FN=— — 显著提升了转化率，r=0.58。
- `holdout` `H07` (eval_design_claim) FP=['C01'] FN=— — 50 条人工标注上准确率 92.0%，数据来自上周那次跑分。
- `holdout` `H12` (cost_claim) FP=— FN=['C05'] — 换小模型让单次成本砍掉一半。

## Limits of this evaluation

- The dev set was used to design the regex rules. The hold-out file was written after those rules were frozen, but the same author saw both, so this is NOT a strictly independent hold-out.
- Gold labels are human judgements of what evidence a sentence supplies; they are not derived from the script's output. False positives and false negatives are deliberately left in the set instead of being patched away; see evals/README.md for the two systematic failure families the hold-out exposed.
- Sample sizes are small; Wilson intervals are wide. Do not read a difference of a few points as an improvement.
- No claim is made about the model's adjudication quality.
