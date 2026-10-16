# 04 — LLM Pipeline (Apertus)

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

Everything about how Skony talks to the model — and, more importantly, how it avoids believing it.

## Model strategy

| Model | Use | Why |
|---|---|---|
| Apertus v1.5 **8B** | Development, CI, batch iteration, demo fallback | Runs self-hosted on ~20 GB RAM; fast feedback |
| Apertus v1.5 **70B** | Final quality runs, evaluation numbers, difficult documents | Higher extraction fidelity on Swiss multilingual text |

Selection is pure configuration: `LLM_NAME` + `LLM_BASE_URL` + `LLM_API_KEY`. One client module (`src/llm/client.py`) is the only file that speaks HTTP to a model. Temperature ≈ 0 for extraction (determinism aids verification and reproducibility).

## Pipeline stages per document

```
segments + offset map
  → 1. prompt build (schema + vocab + segments)
  → 2. Apertus call (structured JSON out, quotes per field)
  → 3. schema validation (Pydantic) ──invalid──→ repair prompt (once) ──invalid──→ review queue
  → 4. verification (quotes → spans, rules)      [deterministic, no LLM]
  → 5. confidence + abstention
  → 6. persist (JSONB + provenance + stats)
```

## Prompt design

**System prompt (skeleton, per language DE/FR/IT/EN):**

```
You extract structured data from Swiss parliamentary documents.
Rules:
- Output ONLY JSON matching the provided schema. No extra keys, no commentary.
- Copy values VERBATIM from the document. Never paraphrase an extracted value.
- For every value, include the exact "quote" substring it comes from and its "page".
- If a value is not present or not legible, output null. Do not guess.
- Use only the controlled vocabulary values listed below for categorical fields.
- Dates: output ISO format; keep the original string in the quote.
- The document language is {language}. Answer field content stays in that language.
```

**User prompt:** affair-type hint (from metadata), controlled vocabularies, then the segmented document with explicit page markers (`⟦page 3⟧`) so quotes can be resolved to pages.

**Why quotes, not offsets:** LLMs are unreliable at arithmetic. Skony asks for the verbatim substring; the *verifier* deterministically resolves it to `(page, span)`. Trust is earned by string matching, not model claims.

## Verification algorithm (`src/verify/`)

```
resolve(quote, page_hint, offset_map):
    for page in [page_hint, *other_pages]:        # hint first, then global
        for matcher in [exact, normalised, fuzzy]:
            hit = matcher.find(quote, page.text)
            if hit: return Provenance(page, hit.span, quote), confidence(matcher)
    return None, 0.0                               # → abstain path

matchers:
    exact      = str.find
    normalised = case-fold, collapse whitespace, NFC unicode (ä/ö/ü/accents)
    fuzzy      = token-sequence ratio ≥ 0.92 (handles OCR noise in scans)
```

Confidence combines: matcher strength (exact 1.0 / normalised 0.9 / fuzzy 0.75), segment quality (scan, handwriting, table penalty), and the model's self-rating (tie-breaker only — never sufficient alone).

## Abstention policy

| Trigger | Result |
|---|---|
| quote not found on any page | field `null`, reason `span_not_found`, doc → review |
| confidence < `SKONY_CONFIDENCE_THRESHOLD` | field kept but `needs_review` (visible, not exported as verified) |
| page flagged illegible (scan/OCR failure) | affected fields `null`, reason `illegible_scan` |
| two segments contradict | `null`, reason `conflicting_sources` |
| schema invalid after repair | whole document → review queue, nothing exported |

Abstention is a *feature* reported in evaluation (coverage vs precision trade-off), not an error to hide.

## Multilingual handling

- Prompt templates per language; vocabulary values stay language-neutral (English keys) with per-language descriptions so a German document still yields `motion`, not `Motion` (that's the quote's job).
- Per-language gold slices guarantee DE and FR are measured separately — no averaging away a weak language.
- UI-level translation (SK-D4) is always labelled `generated` and carries no provenance — clearly separated from extracted content.

## Long documents

- Most affair documents fit in context; when not, extraction runs per logical segment (question / answer / decision blocks from SK-A4) and results are merged by the validator, which re-checks cross-references (e.g. decision date appearing in history).
- Never truncate silently: any document needing chunking is logged with `chunked: true` so evaluation can measure the cost of chunking separately.

## Cost & performance control

- Token, latency, retry and cost (CHF estimate) logged per call → batch reports → the deployment cost sheet.
- Cache keyed by (document hash, prompt version, model) — re-runs are free and diffs between prompt versions are measurable.
- Batch concurrency capped to keep a self-hosted 8B endpoint responsive for the live UI during demos.

## Failure modes (known, documented)

| Failure | Mitigation |
|---|---|
| Model invents plausible value | Verbatim guard rejects it (must be findable) |
| Correct value, wrong/missing quote | Abstain + review — false reject is cheap, false accept is fatal |
| OCR garbage in scans | fuzzy matcher + `illegible_scan` abstention |
| Schema drift after prompt change | `prompt_version` pinned per run; eval re-run required for new versions |
| 8B quality gap on FR/IT | 70B for scored runs; per-language metrics expose the gap honestly |
