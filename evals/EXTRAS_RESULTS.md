# Extra eval suites

> These tables score **deterministic baselines**, not model quality. The baselines are control groups. To score real model adjudication or real triggering, run with `--predictions`. No model score is invented here.

| Suite | Source | Cases | Positive | Reverse | TP | FP | FN | Precision [95% CI] | Recall [95% CI] | F1 | Detection [95% CI] | False alarms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| semantic | deterministic baseline | 20 | 14 | 6 | 12 | 2 | 4 | 85.7% [60.1, 96.0] | 75.0% [50.5, 89.8] | 0.800 | 71.4% [45.4, 88.3] | 33.3% (2/6) |
| trigger | deterministic baseline | 20 | 10 | 10 | 8 | 1 | 2 | 88.9% [56.5, 98.0] | 80.0% [49.0, 94.3] | 0.842 | 80.0% [49.0, 94.3] | 10.0% (1/10) |

## Semantic baseline per check

| Check | TP | FP | FN | Recall |
|---|---|---|---|---|
| C02 | 2 | 1 | 1 | 66.7% |
| C03 | 2 | 1 | 1 | 66.7% |
| C04 | 2 | 0 | 1 | 66.7% |
| C07 | 3 | 0 | 0 | 100.0% |
| C08 | 2 | 0 | 0 | 100.0% |
| C11 | 1 | 0 | 1 | 50.0% |

## Mismatches (kept, not patched away)

- `semantic` `S11` (hidden_contradiction) FP=— FN=['C02'] — 目标集是高置信样本，精确率 98%（n=1200，脚本 scripts/a.py，版本 v3）。
- `semantic` `S12` (hidden_contradiction) FP=— FN=['C04'] — 先在全部数据上挑词，再报告提升 13.8 个百分点。
- `semantic` `S13` (hidden_contradiction) FP=— FN=['C03'] — 标注用的是 searched_job_title，准确率 44.4%。
- `semantic` `S14` (hidden_contradiction) FP=— FN=['C11'] — 任一命中率涨了 7 个点，top-1 没涨就没写进报告。
- `semantic` `S18` (compliant) FP=['C03'] FN=— — 族识别准确率 86.0%（1,581/1,838）。
- `semantic` `S19` (compliant) FP=['C02'] FN=— — 岗位族识别精确率 92.0%。
- `trigger` `T06` (review_report) FP=— FN=['T'] — launch review 里的数字，帮我过一遍
- `trigger` `T09` (suspicious_metric) FP=— FN=['T'] — 这个相关系数 r=0.62 说明模型有效吗
- `trigger` `T20` (lookup_definition) FP=['T'] FN=— — 帮我查一下这个指标口径定义在哪

## What these numbers are NOT

- They are not the model's semantic-adjudication accuracy. The baseline reads structured fields and never reads the claim text; four `hidden_contradiction` cases exist specifically to keep its recall below 1.00.
- They are not trigger accuracy of any real agent harness. The trigger baseline is a handful of intent hints; two should-trigger cases have no hint and one should-not-trigger case contains hints.
- Gold labels were written before running the baseline. Compliant traps (S18, S19, T20) intentionally produce false positives so the reverse test has teeth.
- Sample sizes are 20 per suite; Wilson intervals are wide. Do not read a few points of difference as an improvement.

## Reproduce

```bash
python scripts/eval_extras.py --self-test
python scripts/eval_extras.py --suite all --out evals/EXTRAS_RESULTS.md
python scripts/eval_extras.py --suite semantic --predictions model_semantic.json
python scripts/eval_extras.py --suite trigger --predictions model_trigger.json
```

A `--predictions` file maps every case id to a list of check ids (semantic) or a boolean (trigger). Missing ids are rejected rather than silently treated as negatives.
