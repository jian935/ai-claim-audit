# Audit Rubric v1.0.0

Twelve checks. Six of them (`C01 C05 C06 C09 C10 C12`) have a deterministic
pre-check in `scripts/audit_claims.py`. The other six are judgement calls and
**must be adjudicated by the model for every single claim** — the script lists
them as a mandatory checklist; it does not score them.

A raised check is a **question, not a verdict**. "This number has no stated
denominator" is an observable fact. "The number is fabricated" is an
accusation that requires evidence and must not be made by this skill.

## Severity

| Level | Meaning | Action |
|---|---|---|
| **S1** | The claim cannot be trusted in any direction. Usually a self-confirming eval set, an invalid label source, or a mixed metric definition. | Do not quote the number. Rebuild the measurement. |
| **S2** | Direction may be right, magnitude is unknown. Missing denominator, baseline, hold-out, or uncertainty. | Quote only with an explicit caveat; request the missing number. |
| **S3** | The number is probably fine but cannot be reproduced or is worded too strongly. | Add a pointer, downgrade the verb. |

The severity of a claim is the **highest** severity among its raised checks.
Never average severities.

---

## C01 — Denominator and sample size · machine · S2

**Trigger:** any percentage, rate, ratio, or "k out of n" phrasing.

**Passing evidence:** an explicit denominator *in the same sentence or the
adjacent one* — `n=1167`, `1,167 条 JD`, `out of 1,167`, `分母为…`, `在 45 条人工标注上`.
A denominator attached to a *different* number does not count.

**Ask:** "分母是什么？谁选的？换一个分母这个数会变成多少？"

**Typical disguise:** reporting `49%` when 39 of 79 categories were enumerated,
because `39/79` looks better than the other two defensible denominators. When
several denominators are defensible, all of them must appear on the same screen.

---

## C02 — Self-confirming target set · semantic · S1

**Trigger:** a reported accuracy/precision/recall for a detection, matching, or
classification task.

**Passing evidence:** the positive set is defined by something **external to the
text the model scores** — usually the job title, a human label, or a database
field collected independently.

**Fail:** the target set is "records whose body contains the word X", "queries
the model already answered X on", or any set derived from the predictor's own
output. Such a setup returns precision 1.00 by construction and proves nothing.

**Ask:** "如果我把正文里那个词删掉，这条还会被选进目标集吗？"

---

## C03 — Label provenance · semantic · S1

**Trigger:** any "human-labelled", "ground truth", or "accuracy against labels"
claim.

**Passing evidence:** the label came from the field that actually answers the
question, and that field is named.

**Fail:** using a collection-time search keyword, a crawl category, a platform
queue status, or an algorithm's own score as if it were a human outcome. A
search keyword is what the crawler *looked for*, not what the row *is*. This
has produced a plausible-looking 44.4% that was entirely an artefact.

**Ask:** "这个标签是采集时留下的，还是有人针对这个问题重新标的？"

---

## C04 — Hold-out and leakage · semantic · S1

**Trigger:** a reported improvement, new word/rule/feature, or tuned threshold.

**Passing evidence:** a dev/hold-out split that existed **before** the change was
chosen, and the gain appearing on both sides. A single number measured on the
same data used to pick the change is not an improvement, it is a description.

**Fail:** mining candidate words from all rows and reporting precision on those
same rows; adding few-shot examples taken from the eval set.

**Ask:** "这批数据你在决定改法之前看过吗？改动后有没有一块没动过的集合？"

---

## C05 — Baseline / control · machine · S2

**Trigger:** "improved from X to Y", "lift", "grew", "reduced", any before/after
pair.

**Passing evidence:** a named comparator — rule baseline, previous version,
control group, plain-prompt control, or the same period before launch.

**Fail:** comparing against zero, against a hypothetical, or against a number
measured under a different metric definition. Also fail when the comparator is
named but the two numbers come from different datasets.

**Ask:** "跟什么比？两边是同一份数据、同一个口径吗？"

---

## C06 — Uncertainty · machine · S2

**Trigger:** a correlation coefficient, `r=`, a significance claim, or a small
sample mean.

**Passing evidence:** sample size `n`, an interval or variance, and — for
correlation — the rule that the decision is based on **whether the interval
crosses zero**, not on how large `r` is. For stochastic evaluators, a statement
about run-to-run variability and a fixed seed.

**Fail:** `r=0.62` with no `n`; a single run of an LLM judge with `temperature>0`
presented as a stable score; a mean over 5 trials with no spread.

**Ask:** "区间跨 0 吗？重跑一次会变多少？"

---

## C07 — One metric definition, one source of truth · semantic · S1

**Trigger:** any KPI that appears in more than one document, dashboard, or
funnel stage.

**Passing evidence:** the status enum, positive/negative definition, and mode
labels live in exactly one module that every consumer imports.

**Fail:** "platform queue state counts as positive feedback" in one report but
not in another; `interview` being positive in one mode and neutral in another
without saying so; computing a score over `job_text or job_description` and
silently changing the field later. Mixed definitions make the correlation
number meaningless, not merely imprecise.

**Ask:** "这个状态在别的报表里算正反馈吗？口径改过吗？"

---

## C08 — Data artefacts before model quality · semantic · S1

**Trigger:** a surprisingly high or surprisingly low metric on scraped / logged
text.

**Passing evidence:** deduplication by body text, and boilerplate stripped at
the ingestion boundary, both stated.

**Fail:** four duplicate crawls fabricating `prec=100%`; site disclaimers and
anti-fraud notices dragging a class's precision down to 2.5%; a header/footer
repeated 150+ times per document. The correct fix is an ingestion filter, not
deleting words from a vocabulary or retraining.

**Ask:** "按正文去重了吗？样板文本是在入口剥掉的，还是靠改词表绕过去的？"

---

## C09 — Synthetic data disclosure · machine · S3

**Trigger:** "example", "demo", "sample output", "示例", "演示", or a suspiciously
clean before/after table.

**Passing evidence:** an explicit label that the data is fabricated /
illustrative / mock, **plus** a sentence explaining why it looks good.

**Ask:** "这是真实数据还是编的？如果是编的，为什么它跑出来这么好看？"

---

## C10 — Reproducibility · machine · S3

**Trigger:** "we measured / evaluated / benchmarked", any accuracy or eval-set
claim.

**Passing evidence:** a data version or checksum, a script path or command, and
enough information to re-run it. "See the dashboard" is not reproducibility.

**Ask:** "陌生人拿到仓库，能跑出同一个数吗？"

---

## C11 — One-sided gain · semantic · S2

**Trigger:** an improvement reported for one slice only.

**Passing evidence:** the gain on both dev and hold-out, or on all the slices
that were pre-declared, plus the slices where it did **not** improve.

**Fail:** keyword-level gain while overall accuracy is flat; any-in gain with
top-1 flat; a `.0 → .3` improvement reported without the three families that
got worse. Under an any-in rule the ceiling of a gain is the number of misses
it can recover — simulate that delta first; if it is zero, stop.

**Ask:** "哪个口径没涨？涨的那部分上限是多少？"

---

## C12 — Correlation written as causation · machine · S2

**Trigger:** causal verbs attached to a number (`带来`, `导致`, `使得`, `拉动`,
`归功于`, `led to`, `drove`, `caused`).

**Passing evidence:** an experiment with a control, or an explicit hedge
(`相关`, `可能`, `associated`, `may`).

**Fail:** "the matching score correlates with callbacks, therefore the model
works". When the predicted-score distributions of the positive and negative
groups overlap heavily, no scorer will fix the outcome — report that instead.

**Ask:** "有没有对照组？还是只有一条相关系数？"

---

## Adjudication rules

1. Judge every claim against all 12 checks. Do not stop at the first hit.
2. Prefer the cheapest explanation: artefacts (`C08`) and definitions (`C07`)
   before model quality. Fixing a vocabulary to compensate for dirty data makes
   the number worse.
3. Do not invent the missing number. List it as an explicit requested input.
4. A rewritten claim must be **weaker than or equal to** the original. Never
   strengthen a claim while "fixing" it.
5. Count each problem once. Do not inflate severity by reporting the same
   missing denominator under three check IDs.
6. Close with the limitations of the audit itself (see `output-format.md`).
