# NamEngine Engine Audit Review Guide

Use this guide when reviewing `run_engine_audit.py` CSV output for Baby, Pet, and Business.

## Running the judge pass

Generate the active audit CSV:

```bash
python run_engine_audit.py --rounds 4
```

Then create a judged CSV from the latest audit:

```bash
python judge_engine_audit.py --latest
```

For a stricter blind model spot-check when `OPENAI_API_KEY` is available:

```bash
python judge_engine_audit.py --latest --use-ai --limit 10
```

For a full AI judge pass:

```bash
python judge_engine_audit.py --latest --use-ai
```

The judge script writes:

- `*-judged.csv` with reviewer columns filled
- `*-judged.summary.json` with average score, action counts, and watch rows

The built-in local judge is conservative and deterministic. Use it as a first-pass filter. The AI judge is more useful for taste, quality, and lane-discovery review because it reads the row blind and does not depend only on mechanical pass/fail signals.

## What the audit is testing

NamEngine should behave like a taste-discovery engine, not a one-shot generator.

A strong round should produce:

1. Fresh names with low repetition from prior rounds.
2. Names that stay on the original brief.
3. A distinct discovery lane, such as core fit, adjacent style, wider discovery, hidden gems, callable core, brand-shape alternatives, etc.
4. No avoid-list violations.
5. At least one name a real user might save, shortlist, or react to.

## Reviewer columns

Fill these columns in the CSV:

- `judge_on_brief_1_5`
  - 1 = ignored the brief
  - 3 = partly aligned
  - 5 = clearly understood the brief

- `judge_name_quality_1_5`
  - 1 = weak/cringe/unusable
  - 3 = mixed quality
  - 5 = strong, polished, realistic options

- `judge_lane_discovery_1_5`
  - 1 = feels like a reshuffle or random list
  - 3 = somewhat different angle
  - 5 = clearly explores the stated lane while staying relevant

- `judge_would_save_any`
  - Yes / No / Maybe

- `judge_names_to_cut`
  - List names that should be removed from that round.

- `judge_notes`
  - Short reason: what worked, what felt off, what lane this reveals.

- `action_needed`
  - Optional: engine fix, fixture issue, candidate pool issue, naming-quality issue, no action.

## Simple pass rule

A row is human-green if:

- on-brief >= 4
- name quality >= 4
- lane discovery >= 4
- would save any = Yes or Maybe
- no obviously bad names remain uncut

## How to review quickly

Read each row in this order:

1. `label`
2. `round_number`
3. `lane_label` + `lane_description`
4. `top_names`
5. `brief_json` only if the fit is unclear

Then score the judge columns. Do not try to perfect every name. The key question is:

> Did this round help the user discover, confirm, or reject a taste lane?
