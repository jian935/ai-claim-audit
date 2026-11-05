# Contributing

Three kinds of contribution: a new labelled case, a wider regex, a new check.
All three must survive the same discipline this skill audits other people by.

## Non-negotiable rules

1. **Never define a target set by keyword presence.** A new case belongs to a
   claim `category`; a case is flawed because a human judges that evidence is
   missing. Defining "cases whose text contains X" makes the score 1.00 by
   construction and proves nothing.
2. **Fix the label, not the engine, when the label is wrong.** When a case and
   the script disagree, decide which is wrong first. If the label is wrong,
   correct the label. Do not bend a rule to agree with a bad label. If the
   engine is wrong, keep the mismatch visible in `RESULTS.md`.
3. **Every rule change needs a reverse test.** Tightening or deleting a rule
   must come with assertions that the `compliant` cases still pass. Check that
   the thing being removed is not load-bearing for another check first.
4. **Simulate the ceiling before widening a rule.** Count how many real misses
   the change can recover. If that number is zero, stop — no change.
5. **Freeze before a new hold-out.** Design on `dev.json`; freeze
   `scripts/audit_claims.py`; only then write a new `holdout-*.json` with
   different wording. Report the score drop honestly.
6. **Keep false positives and false negatives.** `RESULTS.md` is generated and
   must not be hand-edited to look better. Mismatches stay with an explanation.
7. **Deduplicate by body text** before computing any case-level statistic.
   Duplicate examples can fabricate perfect scores.
8. **Require the gain on both sides.** A rule change that helps dev but hurts
   hold-out is not an improvement. Inspect the cases by hand.
9. **Never invent a number.** Every number in a README must come from a command
   in this repo. Demo/sample data must be labelled as fabricated and must say
   *why* it looks good.
10. **Update both READMEs.** Run `python scripts/check_docs.py` — the English
    and Chinese versions must carry the same key numbers.

## Adding a labelled case

```json
{
  "id": "D19", "split": "dev", "category": "accuracy_claim",
  "text": "...",
  "expected_machine_checks": ["C01"],
  "semantic_checks": ["C02"],
  "note": "Why a reviewer should raise this, in one sentence."
}
```

- `compliant` cases must have `expected_machine_checks: []`.
- `semantic_checks` are documentation for human review; they are not scored.
- Write the `note` before running the script, so the label is not derived from
  the script's output.
- For `semantic.json`, include the full `material` object and set
  `expected_verdict`; for `trigger.json`, set `intent` and `should_trigger`.
  Both files are scored by `scripts/eval_extras.py`, and every case id must
  appear in any `--predictions` file.

## Before opening a PR

```bash
python scripts/audit_claims.py --self-test
python scripts/eval_extras.py --self-test
python scripts/run_evals.py --split all --out evals/RESULTS.md
python scripts/eval_extras.py --suite all --out evals/EXTRAS_RESULTS.md
python scripts/check_docs.py
```

CI re-runs all of the above, then `git diff --exit-code` on the three generated
reports (`evals/RESULTS.md`, `evals/EXTRAS_RESULTS.md`,
`examples/audit_report.md`). Any change to a rule or a case moves a golden
file and turns the PR red. Never hand-edit a golden file to make CI green:
regenerate it, inspect the diff, and commit it as part of the change.

If `evals/RESULTS.md` changed, paste the new table into both READMEs and keep
dev, hold-out and all three rows. If a new systematic failure appears, add a
row to `evals/README.md` instead of quietly fixing it on the same cases used
to measure it.

## Release packaging

Never use a generic recursive packager once this folder is a git repository.
During the 2026-11-05 checkup one walked `.git/` and shipped 47 history
objects in a 65-entry zip (the correct release has 18 entries). Build the
release zip from tracked files only:

```bash
python - <<'PY'
import zipfile, subprocess
files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
with zipfile.ZipFile("ai-claim-audit.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f, "ai-claim-audit/" + f)
print(len(files), "files, no .git, no __pycache__")
PY
```

Validate the skill structure separately; validation and packaging are two
different jobs.

Adding or editing a case in `semantic.json` / `trigger.json` also requires
regenerating the blind question sheet and the answer template:

```bash
python scripts/eval_extras.py --make-blind-pack
python scripts/eval_extras.py --make-template
```

CI rebuilds both and fails if they are stale. Filled-in predictions belong in
`evals/my_predictions.json` (gitignored), never in the tracked template. See
[`evals/BLIND_EVAL.md`](evals/BLIND_EVAL.md) for the full blind-eval procedure
and the metadata a published model score must carry.

## Style

- `SKILL.md` uses imperative form and stays under 5k words; detailed material
  belongs in `references/`.
- Reports use the template in `references/output-format.md`, including the
  mandatory limitations section.
- No private, submission or account data anywhere in this repository. Only
  aggregate numbers and method.
