> Archived Liebefeld planning draft, preserved 15 October 2026.
> Placeholder metrics and described services are not measured results or
> implemented online features. Use the [active report](../../track_2a/technical_report.md)
> and [current direction](../16-project-direction.md).

# Skony — Technical Report

*Hack Apertus Liebefeld, Track 2A · Skeleton v0.1 (14 Oct 2026) — numbers are filled from `make eval` at submission time. Anything in ⟨angle brackets⟩ is a placeholder, not a result.*

## 1. Summary

Skony converts Swiss parliamentary PDFs into a versioned common schema using Apertus v1.5, with verbatim-verified provenance for every value, mechanical abstention where extraction is unreliable, a human review workbench, and cited cross-parliamentary answers. Evaluated on ⟨N⟩ gold documents across ⟨B⟩ bodies and ⟨L⟩ languages: auto-accept precision ⟨0.xx⟩, provenance coverage ⟨100%⟩, field F1 ⟨0.xx⟩ (DE) / ⟨0.xx⟩ (FR).

## 2. Architecture

See `docs/02-architecture.md`. Pipeline: ingest (detect, segment, offset map) → Apertus structured extraction (schema-first prompts, quotes not offsets) → deterministic verifier (quote→span resolution, consistency rules, confidence) → abstention → PostgreSQL → FastAPI → review workbench + cited query UI. Single LLM gateway configured by `LLM_NAME` / `LLM_BASE_URL` / `LLM_API_KEY`. Apertus-8B for iteration, 70B for scored runs. Full container diagram and repository layout in the docs.

## 3. The representation model

Versioned schema (`skony.schema.v1`) with controlled vocabularies (affair types, actor roles, procedural states, decision outcomes), per-field provenance/confidence/origin, and first-class `null` + reason codes. Mapped partially to Akoma Ntoso, Popolo, eCH (Fachgruppe Politische Geschäfte) and Docling — see `docs/03-data-model.md`.

## 4. Evaluation

- **Gold set:** ⟨N⟩ documents, stratified ⟨bodies × languages × digital/scanned × affair types⟩, field-level human annotation with spans, in `data/gold/`.
- **Method:** fixed deterministic scorer; pinned `model_name` + `prompt_version` + `schema_version` + gold commit; dev slice used for prompt tuning, gold set untouched until scored runs.
- **Baselines:** (a) Docling-only structure, (b) ad-hoc unconstrained prompting.

### Results (from `make eval`, commit ⟨hash⟩)

| Field | P | R | F1 | Abstain |
|---|---|---|---|---|
| affair_type | ⟨⟩ | ⟨⟩ | ⟨⟩ | ⟨⟩ |
| submitters | ⟨⟩ | ⟨⟩ | ⟨⟩ | ⟨⟩ |
| question_text | ⟨⟩ | ⟨⟩ | ⟨⟩ | ⟨⟩ |
| answer_text | ⟨⟩ | ⟨⟩ | ⟨⟩ | ⟨⟩ |
| decision | ⟨⟩ | ⟨⟩ | ⟨⟩ | ⟨⟩ |
| **by language** | DE F1 ⟨⟩ | FR F1 ⟨⟩ | | |
| **vs baselines** | Docling F1 ⟨⟩ | ad-hoc F1 ⟨⟩ | Skony F1 ⟨⟩ | |

Cost/latency: ⟨tokens/doc⟩, ⟨CHF/doc⟩ (8B), ⟨CHF/doc⟩ (70B), p95 ⟨s⟩.

### Error analysis (top failure modes, with examples)

1. ⟨e.g. OCR garbage on scanned annex pages → abstain, correct behaviour⟩
2. ⟨e.g. FR date formats missed in prompt v1.2, fixed v1.3, numbers shown⟩
3. ⟨e.g. multi-submitter lists truncated by 8B, resolved by 70B⟩

## 5. Insight: is a common schema feasible?

⟨The core deliverable — written from measured slices:⟩
- **Generalises:** ⟨e.g. type, submitters, dates, decision across all tested bodies⟩
- **Partially:** ⟨e.g. procedural history granularity differs cantonal vs municipal⟩
- **Breaks:** ⟨e.g. body X's combined question+decision layout; vocabulary gaps⟩
Per the challenge brief, a convincing partial/negative answer counts as success — this section is the honest one.

## 6. Limitations

- Scans/handwriting degrade extraction → abstention (coverage/precision trade-off, measured above).
- 8B vs 70B gap on FR/IT ⟨quantified⟩.
- Gold set size ⟨N⟩ limits statistical power; per-body slices are indicative.
- No real-time scraping; corpus is the provided export/files snapshot.
- Chunking of very long documents ⟨measured effect⟩.

## 7. Running the project

```bash
make run    # Docker: db+api+worker+ui, seeded demo corpus, offline-capable
make eval   # reproduce all numbers above from committed artefacts
make test   # verifier/validator unit tests incl. seeded hallucinations
```

Environment: `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` (see `.env.example`). Self-hosted Apertus-8B profile included (`docker compose --profile local-llm up`). Data ≤ 100 MB in `data/`.

## 8. Ethics & licence

Conservative extraction per the challenge brief (verbatim guard, extracted/inferred/manual labelling, abstain-don't-guess). Corpus = already-published parliamentary material. Code Apache-2.0; all artefacts openly reusable. No external commercial LLM anywhere in the dependency tree.
