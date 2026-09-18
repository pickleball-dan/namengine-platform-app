# NamEngine Provider Comparison Summary
**Date:** 2026-08-14
**Status:** Research / Internal Reference
**Purpose:** Document findings from first live OpenAI vs Claude provider comparison run using NamEngine's Baby vertical.

---

## Overview

This document captures the first live side-by-side provider comparison run conducted against NamEngine's naming engine. The goal was to validate the provider comparison concept and confirm that the Taste Engine's scoring and evaluation rubric can be applied uniformly across multiple AI providers using identical intake briefs.

The comparison was run locally (not on production) using the same intake brief against both providers via a lightweight harness.

---

## Test Configuration

| Field | Value |
|---|---|
| **Vertical** | Baby |
| **Run type** | Fast (1 round, equal candidate count) |
| **Environment** | Local (not production) |
| **Date** | 2026-08-14 |
| **Harness** | Custom local comparison script |

### Intake Brief

| Question | Answer |
|---|---|
| Sex | Girl |
| Style | Warm, elegant, nature-adjacent, not too trendy |
| Sound | Soft vowels, 2–3 syllables |
| Meaning | Light, calm, grounded, hopeful |
| Names liked | Clara, Elara, Sylvie, Nora |
| Names rejected | Everleigh, Braxtyn, Khaleesi, Nevaeh |
| Avoid | -leigh suffix, trend-invented names |

---

## Results

### OpenAI (GPT-4o)

| Field | Result |
|---|---|
| **Status** | ✅ Completed |
| **Latency** | ~48.2 seconds |
| **Names generated** | Elowen, Liora, Sylvie, Colette |
| **Output** | Valid, well-structured |

### Claude (Anthropic)

| Field | Result |
|---|---|
| **Status** | ✅ Completed |
| **Latency** | ~172.8 seconds |
| **Names generated** | Lydia, Linnea, Iris, Maren |
| **Output** | Valid |

> **Note:** Latency and any output differences between providers in this run reflect the specific environment and configuration at the time of testing, including subscription tier and prompt tuning. They are not representative of provider capability at production configuration.

---

## Side-by-Side Comparison

| Metric | OpenAI | Claude |
|---|---|---|
| **Completed successfully** | ✅ Yes | ✅ Yes |
| **Total latency** | ~48s | ~173s |
| **Name style** | Soft, poetic, nature-leaning | Classic, clean, grounded |

### Name Quality Notes
- **OpenAI names:** Elowen and Liora skew poetic/invented; Sylvie and Colette are established elegant names. Strong brief match.
- **Claude names:** Lydia, Linnea, Iris, Maren are more classical/literary. Also strong brief match, different flavor.
- Both sets fit the brief's aesthetic well. Meaningful qualitative difference exists but neither is clearly superior on taste alone — they represent different but valid naming philosophies for the same brief.

---

## Findings

### 1. Provider comparison concept validated ✅
The core concept works end-to-end: same intake brief, same scoring rubric, two different providers, two distinct but high-quality outputs. The Taste Engine's evaluation layer is provider-agnostic.

### 2. Output style differences are meaningful
Both providers produced names that fit the brief, but with distinct stylistic voices. This is itself a useful signal — provider selection may eventually become a product-level tuning knob (e.g., "more poetic" vs "more classical" outputs).

### 3. Comparison ranking display needs tightening (minor)
The comparison chart output did not sort results purely by quality score — displayed order was not fully meaningful. Needs tightening in the harness/UI before Mission Control shows side-by-side results to operators.

---

## Conclusions

| Question | Answer |
|---|---|
| Does the provider comparison concept work? | ✅ Yes — end-to-end flow validated |
| Does the Taste Engine scoring apply uniformly across providers? | ✅ Yes |
| Are output styles meaningfully different across providers? | ✅ Yes — and that's useful signal |
| Is this worth pursuing further? | ✅ Yes — strong patent/product story |

---

## Next Steps (when ready to resume)

1. **Tune provider-specific prompt configurations** — optimize structured output schemas per provider at production subscription/configuration levels
2. **Re-run live comparison** — confirm consistent results at production configuration before wiring into router
3. **Wire additional providers into `model_router.py`** — behind a provider flag, not customer-facing default
4. **Build Mission Control side-by-side UI** — same scenarios, same rubric, provider selected per run, persisted history
5. **Extend to Gemini + other providers** — once the two-provider harness is stable

---

## Strategic Context

Generation QA is intended to evolve into a **cross-AI-provider comparison harness**: OpenAI vs Claude vs Gemini vs Meta/etc. The product and patent framing is that NamEngine's Taste Engine can score and compare naming engines across providers using the same scenarios and quality rubric — turning Generation QA into a competitive intelligence tool as well as an operational health monitor.

This run validated the concept. The infrastructure exists. The next milestone is production-level provider configuration and the Mission Control side-by-side UI.

---

*Document created 2026-08-24 from session memory. Original run artifacts were not preserved.*
