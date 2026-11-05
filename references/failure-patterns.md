# Failure Patterns

Real traps distilled from building and measuring a job-matching engine on two
public datasets (1,167 English JDs and 8,674 Chinese JDs). Numbers here are
aggregate observations from that project, included as **reasoning examples**,
not as benchmarks for this skill. All examples are paraphrased and contain no
personal or submission data.

Use this file when a claim looks plausible but something feels off. Each
pattern pairs a symptom with the fix that actually worked, because the obvious
fix is usually wrong.

---

### P1 · Precision 1.00 that proves nothing → `C02`

**Symptom:** a keyword/ability detector scores 100% on its target set.
**Wrong fix:** celebrate, then tune the threshold.
**Real cause:** the target set was defined as "rows whose body contains the
keyword". The detector is being graded on whether it finds the thing the set
was built from.
**Right fix:** define the target set from an external field (the job title),
never from the text being scored. Re-measure. Expect a large drop; that drop is
the honest number.

### P2 · A 44.4% that was never real → `C03`

**Symptom:** accuracy looks reasonable, but the label column is a
collection-time search keyword.
**Wrong fix:** add more keywords to the taxonomy.
**Real cause:** the crawler's search term describes what was *looked for*, not
what the row *is*. Noise is baked into the label.
**Right fix:** label from the cleaned `job_title`, and only score rows whose
title unambiguously determines the family.

### P3 · A class with 2.5% precision → `C08`

**Symptom:** one class is inexplicably terrible while others are fine.
**Wrong fix:** delete that class's keywords.
**Real cause:** site disclaimers ("招聘声明") and anti-fraud notices ("证照")
were counted as real job text.
**Right fix:** strip boilerplate at the ingestion boundary — split on sentence
boundaries and treat any sentence appearing ≥150 times as boilerplate. The same
class then measured above 90% with **no vocabulary change at all**.

### P4 · Four duplicate rows fabricate 100% → `C08`

**Symptom:** a mined candidate word has perfect precision on four hits.
**Wrong fix:** lower the support threshold.
**Real cause:** the same posting was crawled four times.
**Right fix:** deduplicate the document-frequency table by body text before
computing any precision.

### P5 · A correlation that changes whenever the wording changes → `C07`, `C06`

**Symptom:** `r` moves between reports and nobody touched the model.
**Wrong fix:** try a new scoring function.
**Real cause:** the positive-feedback definition drifted — "offer only" in one
run, "any HR action" in another, platform queue states silently included in a
third. Also: `final_score` was an algorithm-generated label being treated as a
human outcome.
**Right fix:** put the status enum, positive-feedback definition, and mode
labels in one module that every consumer imports; add tests that lock them.
Then report `r` with `n` and a 95% interval, and decide by whether the
interval crosses zero.

### P6 · A low `r` no model can fix → `C12`, `C06`

**Symptom:** correlation between predicted fit and real callbacks is near zero.
**Wrong fix:** swap the scorer, add features, tune weights.
**Real cause:** the predicted-score distributions of the positive and negative
groups overlap almost completely. The outcome simply is not related to the
predictor in this data.
**Right fix:** report the overlap, state the boundary of the method, and stop.
Also exclude records with no original JD text from the correlation — they
belong in the funnel, not in `r`.

### P7 · 49% that hides two other denominators → `C01`

**Symptom:** "we cover 49% of the taxonomy".
**Real cause:** only 39 of 79 categories were enumerated, so 39/79 is the
flattering ratio; two other defensible denominators exist.
**Right fix:** show all three ratios on the same screen, with the conservative
`supported/79` as the headline.

### P8 · A gain that only exists on the data used to pick it → `C04`, `C11`

**Symptom:** a new context constraint improves accuracy by +13.8 points.
**Wrong fix:** ship it and quote the number.
**Real cause:** unless the constraint was chosen on a dev split and measured on
untouched hold-out data, the gain is a description of the tuning set.
**Right fix:** dev/hold-out split, require the gain on both sides, inspect the
cases by hand, and note that title/body contradictions in the source data put a
ceiling on what any rule change can recover. Simulate the achievable delta
before adding a word: if the ceiling is zero, stop.

### P9 · A clean demo table that was typed by hand → `C09`

**Symptom:** a before/after table with perfectly round numbers.
**Right fix:** label it as fabricated/illustrative at the point of use, and add
one sentence explaining *why* it looks good. Never let demo numbers migrate
into a README metric table.

### P10 · LLM eval scores that move by ±2 cases → `C06`, `C10`

**Symptom:** the same prompt answers differently on repeated concurrent runs.
**Real cause:** `temperature>0` plus duplicate bodies, no cache.
**Right fix:** cache responses, pin a seed where possible, and state the
run-to-run variability next to the number.

### P11 · A rule tightened without a reverse test → `C04`

**Symptom:** precision goes up, something else silently breaks.
**Real cause:** the removed word was load-bearing for a different class.
**Right fix:** before deleting or narrowing any rule, add a regression test
that asserts the old behaviour still holds for the cases it used to serve.
When a label turns out to be wrong, fix the label — do not bend the engine to
agree with a bad label.

---

## Order of diagnosis

`C08` artefacts → `C07` definitions → `C03` labels → `C02` target set →
`C04` split → `C05` baseline → `C06` uncertainty → `C01` denominator →
`C11` slices → `C12` causation → `C09` disclosure → `C10` reproducibility.

Changing a vocabulary to compensate for a problem earlier in this list has
been measured to make accuracy **worse**, not better.
