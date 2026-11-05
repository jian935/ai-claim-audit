# AI Claim Audit — deterministic pre-check

> A raised check is a **question**, not a verdict. Semantic checks are not scored by this script; see the mandatory checklist below.

Scanned 7 claim(s); 5 raised at least one question; 10 question(s) total.

| # | Claim | Raised | Sev | Question to answer |
|---|---|---|---|---|
| Q01 | 模型准确率达到 94%，下周上线。 | C01, C10 | S2 | 分母是什么？谁选的？换一个分母这个数会变成多少？ / 陌生人拿到仓库，能跑出同一个数吗？ |
| Q02 | 加了语境约束后，族识别准确率提升了 13.8 个百分点。 | C01, C05, C10 | S2 | 分母是什么？谁选的？换一个分母这个数会变成多少？ / 跟什么比？两边是同一份数据、同一个口径吗？ / 陌生人拿到仓库，能跑出同一个数吗？ |
| Q03 | 新版本让任务完成率从 62% 提升到 89%。 | C01, C05, C12 | S2 | 分母是什么？谁选的？换一个分母这个数会变成多少？ / 跟什么比？两边是同一份数据、同一个口径吗？ / 有没有对照组？还是只有一条相关系数？ |
| Q04 | 匹配分与实际回复的相关系数 r=0.62，证明匹配模型有效。 | C06 | S2 | 区间跨 0 吗？重跑一次会变多少？ |
| Q05 | 示例数据里 10 条全部通过，效果稳定，可以直接对外引用。 | C09 | S3 | 这是真实数据还是编的？为什么它跑出来这么好看？ |
| Q06 | 目标集取正文里含该能力词的记录，精确率 1.00（n=1838，脚本 scripts/x.py，版本 v1）。 | — | — | — |
| Q07 | 在 1,167 条 JD 的留出集上，规则引擎的岗位族识别准确率为 93.6%，n=1167，复现脚本 scripts/real_eval_family.py，数据版本 2026-10-28。 | — | — | — |

## Mandatory model adjudication checklist

For **every** claim above, decide these six checks using `references/audit-rubric.md` and `references/failure-patterns.md`:

- **C02 Self-confirming target set** (S1) — 删掉正文里那个词，这条还会被选进目标集吗？
- **C03 Label provenance** (S1) — 这个标签是采集时留下的，还是有人针对这个问题重新标的？
- **C04 Hold-out and leakage** (S1) — 决定改法之前看过这批数据吗？有没有一块没动过的集合？
- **C07 One definition, one source of truth** (S1) — 这个状态在别的报表里算正反馈吗？口径改过吗？
- **C08 Data artefacts before model quality** (S1) — 按正文去重了吗？样板文本是在入口剥掉的，还是靠改词表绕过去的？
- **C11 One-sided gain** (S2) — 哪个口径没涨？涨的那部分上限是多少？

Do not conclude from the machine-raised rows alone. Do not invent missing numbers. A rewritten claim must be weaker than or equal to the original.

## Limitations of this audit

This is a regex pre-check over the literal wording of a claim. It can detect a missing denominator, a missing comparator, a missing interval, an undisclosed demo, a missing reproduction pointer, and causal verbs. It CANNOT see the dataset, the label source, the train/test split, the metric definition in code, or duplicated rows. Six semantic checks are listed for mandatory model adjudication and are not auto-scored. A clean pre-check is not evidence that a claim is true.

_ai-claim-audit v1.0.0 · MIT · jian935_
