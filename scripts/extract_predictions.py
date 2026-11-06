#!/usr/bin/env python3
"""Turn a model's raw blind-eval reply into a validated predictions file.

    python scripts/extract_predictions.py --raw evals/raw_reply.txt
    python scripts/extract_predictions.py --stdin < evals/raw_reply.txt
    python scripts/extract_predictions.py --self-test

Models rarely return bare JSON: they wrap it in ```json fences, add a preamble,
or miss an id. This tool extracts the first JSON object containing the expected
suites, validates every answer strictly, and only then writes the gitignored
answers file. It never guesses an answer and never fills a gap with a default —
an unanswered case must be re-asked, not silently scored as a negative.

Zero dependencies, standard library only. Not called by CI's regression gate;
run --self-test locally (and in CI's self-test step) to keep the checks honest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "evals" / "predictions_template.json"
DEFAULT_OUT = ROOT / "evals" / "my_predictions.json"
SEMANTIC_CHECKS = ("C02", "C03", "C04", "C07", "C08", "C11")


class ExtractError(Exception):
    """A friendly, actionable error instead of a traceback."""


def find_json_object(text: str) -> dict:
    """Find the first JSON object that looks like a prediction payload."""
    decoder = json.JSONDecoder()
    for pos, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[pos:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("semantic" in obj or "trigger" in obj):
            return obj
    raise ExtractError(
        "no JSON object with a 'semantic'/'trigger' key found. "
        "Copy the model's WHOLE reply into the raw file, including the JSON block."
    )


def _expected_ids() -> dict[str, set[str]]:
    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    return {k: set(v) for k, v in tpl.items() if k in ("semantic", "trigger")}


def validate(raw: dict) -> dict:
    """Strictly validate every answer. Returns a normalised, ordered payload."""
    if not isinstance(raw, dict):
        raise ExtractError("the model reply must be one JSON object")
    expected = _expected_ids()
    absent = [k for k in expected if k not in raw]
    if absent:
        raise ExtractError(f"missing suite(s): {', '.join(absent)} — both are required")

    out: dict[str, dict] = {}
    for suite, ids in expected.items():
        block = raw[suite]
        if not isinstance(block, dict):
            raise ExtractError(
                f"'{suite}' must be an object mapping case id -> answer, "
                f"not {type(block).__name__}. Re-ask the model for the required format."
            )
        extra = sorted(set(block) - ids)
        missing = sorted(ids - set(block))
        unanswered = sorted(k for k in ids if block.get(k, "absent") is None)
        if extra:
            raise ExtractError(f"unknown id(s) in '{suite}': {extra[:6]}")
        if missing:
            raise ExtractError(f"'{suite}' is missing {len(missing)} id(s): {missing[:6]}")
        if unanswered:
            raise ExtractError(
                f"'{suite}' has {len(unanswered)} unanswered (null) id(s): "
                f"{unanswered[:6]} — re-ask the model, do not fill them in yourself"
            )

        clean: dict[str, object] = {}
        for cid in sorted(ids):
            value = block[cid]
            if suite == "semantic":
                if not isinstance(value, list):
                    raise ExtractError(f"{cid}: semantic answer must be a list, got {value!r}")
                bad = [x for x in value if x not in SEMANTIC_CHECKS]
                if bad:
                    raise ExtractError(f"{cid}: unknown check id(s) {bad}")
                clean[cid] = list(dict.fromkeys(value))  # de-duplicate, keep order
            else:
                if isinstance(value, bool):
                    clean[cid] = value
                elif value in ("T", ["T"]):
                    clean[cid] = True
                elif value in ([], "F", "false", "no"):
                    clean[cid] = False
                else:
                    raise ExtractError(
                        f"{cid}: trigger answer must be true/false, got {value!r}"
                    )
        out[suite] = clean
    return out


def _blank_payload() -> dict:
    """A syntactically valid payload used by --self-test. NOT a model answer."""
    expected = _expected_ids()
    return {
        "semantic": {cid: [] for cid in expected["semantic"]},
        "trigger": {cid: False for cid in expected["trigger"]},
    }


def self_test() -> None:
    good = _blank_payload()
    wrapped = "Sure! Here is the result:\n\n```json\n" + json.dumps(good) + "\n```\nHope it helps."
    assert len(validate(find_json_object(wrapped))["semantic"]) == 20

    cases = [
        ("missing id", {"semantic": {k: v for k, v in good["semantic"].items() if k != "S07"},
                        "trigger": good["trigger"]}, "missing"),
        ("null answer", {"semantic": {**good["semantic"], "S03": None},
                         "trigger": good["trigger"]}, "unanswered"),
        ("unknown check", {"semantic": {**good["semantic"], "S01": ["C99"]},
                           "trigger": good["trigger"]}, "unknown check"),
        ("bad trigger", {"semantic": good["semantic"],
                         "trigger": {**good["trigger"], "T02": "maybe"}}, "true/false"),
        ("semantic not a list", {"semantic": {**good["semantic"], "S01": "C02"},
                                 "trigger": good["trigger"]}, "must be a list"),
        ("unknown id", {"semantic": {**good["semantic"], "S99": []},
                        "trigger": good["trigger"]}, "unknown id"),
        ("missing suite", {"semantic": good["semantic"]}, "missing suite"),
    ]
    for label, payload, fragment in cases:
        try:
            validate(payload)
        except ExtractError as exc:
            assert fragment in str(exc), f"{label}: unexpected message {exc}"
        else:
            raise AssertionError(f"{label}: should have been rejected")
    try:
        find_json_object("I cannot answer that.")
    except ExtractError:
        pass
    else:
        raise AssertionError("prose-only reply should have been rejected")
    assert validate(good)["trigger"]["T01"] is False
    print("self-test: 9/9 passed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, help="file holding the model's whole reply")
    ap.add_argument("--stdin", action="store_true", help="read the reply from stdin")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0
    if bool(args.raw) == bool(args.stdin):
        print("ERROR: pass exactly one of --raw <file> or --stdin", file=sys.stderr)
        return 2
    try:
        if args.raw:
            if not args.raw.exists():
                raise ExtractError(f"raw reply file not found: {args.raw}")
            text = args.raw.read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        payload = validate(find_json_object(text))
    except ExtractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    sem_hits = sum(len(v) for v in payload["semantic"].values())
    sem_empty = sum(not v for v in payload["semantic"].values())
    tri_true = sum(payload["trigger"].values())
    print(f"validated: {len(payload['semantic'])} semantic + "
          f"{len(payload['trigger'])} trigger answers")
    print(f"  semantic: {sem_hits} check hits, {sem_empty} cases with no check")
    print(f"  trigger: {tri_true} should-trigger / "
          f"{len(payload['trigger']) - tri_true} should-not-trigger")
    shown = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"wrote {shown}")
    print("next: python scripts/eval_extras.py --suite all "
          f"--predictions {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
