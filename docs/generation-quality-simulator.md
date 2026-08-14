# NamEngine Generation Quality Simulator

Local QA harness for running realistic user-input scenarios through NamEngine generation.

## Why it exists

The simulator gives NamEngine a repeatable quality loop:

- realistic baby, pet, and business intake scenarios
- generated outputs captured for review
- deterministic anomaly checks before/after engine changes
- compact `summary.json` that Mission Control can read later

It is intentionally local-first. Generated run artifacts are ignored by Git.

## Commands

Fast smoke run:

```bash
python scripts/simulate_generation_quality.py --fast
```

Full local fallback run:

```bash
python scripts/simulate_generation_quality.py --full
```

Live AI run, explicit only:

```bash
python scripts/simulate_generation_quality.py --full --use-ai
```

Filter by vertical:

```bash
python scripts/simulate_generation_quality.py --vertical baby
```

Filter by scenario:

```bash
python scripts/simulate_generation_quality.py --scenario baby-classic-soft-free-preview
```

## Inputs

Scenario fixtures live at:

```text
tests/fixtures/generation_scenarios.json
```

Each scenario has:

- `id`
- `label`
- `mode`: `fast` or `full`
- `vertical`
- `rounds`
- `expected_count`
- `inputs`
- `expected_signals`
- `avoid_names`

The structure is vertical-agnostic. New verticals can be added by registering the vertical and adding fixture rows.

## Outputs

Runs write to:

```text
qa-artifacts/generation-runs/<run-id>/
```

Each run writes:

- `summary.json` — compact anomaly/status summary
- `report.md` — human-readable review report
- `results.json` — full per-scenario outputs

Latest summaries are copied to:

```text
qa-artifacts/generation-runs/latest/summary.json
qa-artifacts/generation-runs/latest/report.md
```

That `latest/summary.json` is the future Mission Control integration point.

## Current anomaly checks

The first version checks deterministic structure:

- generation errors
- too few results
- empty names
- duplicate normalized names
- avoid-list names appearing
- malformed names
- legacy `maybe` signal in result payloads

It does not pretend to fully judge taste quality yet. Human review and/or a later AI blind judge can build on the saved reports.
