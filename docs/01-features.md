# 01 — Feature Catalog

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

Every feature of Skony, grouped by module. Priorities use MoSCoW (**M**ust / **S**hould / **C**ould / **W**on't-for-hackathon). Status as of 14 Oct 2026: everything is `planned` unless noted.

---

## A. Ingestion & Pre-processing

### SK-A1 — Corpus import from OpenParlData
Import parliamentary affairs and their source documents from OpenParlData.
- Supports: bulk export import (files.openparldata.ch/exports/), API fetch (api.openparldata.ch/v1/), direct PDF + pre-extracted Tika/PDFBox text (files.openparldata.ch/doc/).
- Stores affair metadata (title, type, contributors, dates, status, events) alongside document references.
- **Acceptance:** given a body ID (e.g. Nidau 743), import all its affairs + linked documents into PostgreSQL without manual steps.
- **Priority:** M

### SK-A2 — Document type detection
Classify each document as born-digital vs scanned, and detect OCR need.
- Heuristics: text-layer presence, character density, image-only pages.
- Scanned/image-only pages are flagged and routed to the OCR path (Tesseract) or marked `unreadable → review`.
- **Acceptance:** detection labels agree with manual check on ≥ 95% of a 100-doc sample.
- **Priority:** M

### SK-A3 — Language detection
Per-document (and per-page where mixed) language identification: DE / FR / IT / EN / other.
- Drives prompt language selection and per-language evaluation slicing.
- **Acceptance:** ≥ 98% accuracy on a labelled sample; unknown languages fall back to DE with a `language_uncertain` flag.
- **Priority:** M

### SK-A4 — Layout segmentation
Split documents into logical blocks: header (body, date, session), affair title, question text, answer text, decision block, signatures/stamps, tables, annexes.
- Uses Docling where it helps; falls back to rule-based segmentation on Tika text.
- Segments carry page numbers and offsets — the raw material for provenance.
- **Acceptance:** every downstream extraction prompt receives segmented input with page/offset maps; a debug view shows segment boundaries.
- **Priority:** M

### SK-A5 — Pre-cached demo dataset
A fixed, versioned demo corpus (≤ 100 MB per submission rules) of 3–5 bodies × 2 languages, shipped in `data/` so the demo never touches the network.
- **Acceptance:** `make run` on a clean checkout with no internet produces a fully working demo on this corpus.
- **Priority:** M

---

## B. Extraction Pipeline (Apertus)

### SK-B1 — Schema-first structured extraction
Extract a `ParliamentaryAffair` object (see [03-data-model](03-data-model.md)) from each document using Apertus with a strict JSON schema.
- One prompt family per affair type; the schema — not the model — dictates shape. No invented keys.
- Controlled vocabularies enforced for affair type, actor roles, procedural states, decision outcomes.
- **Acceptance:** 100% of outputs validate against the Pydantic model; invalid outputs are retried once with a repair prompt, then routed to review.
- **Priority:** M

### SK-B2 — Provenance capture
Every extracted field records: `document_id`, `page`, character `span`, and the verbatim `quote` it was grounded in.
- Implemented via offset maps from SK-A4; the model returns quotes, the verifier resolves them to spans (see SK-B3) — the model is never trusted to produce offsets itself.
- **Acceptance:** clicking any value in the UI highlights the exact source span in the PDF/text view.
- **Priority:** M

### SK-B3 — Hallucination guard (verbatim verification)
Deterministic post-check: every extracted value's `quote` must be findable in the source text.
- Matching: exact → whitespace/case-normalised → unicode-normalised (ä/ö/ü, accents) → fuzzy (token-level, threshold).
- On failure: field set to `null`, `extraction_status=unverified`, document queued for human review. **Never auto-correct to a plausible value.**
- **Acceptance:** seeded-hallucination test suite (N deliberately wrong outputs) is caught at 100%; false-reject rate measured and reported.
- **Priority:** M

### SK-B4 — Confidence scoring & abstention
Each field carries a confidence signal derived from verifier outcome + model self-rating + segment quality (scanned, handwriting, tables).
- Below threshold → abstain: value `null`, reason code (`low_confidence`, `span_not_found`, `conflicting_sources`, `illegible_scan`), routed to review queue.
- Embodies the brief: *"where extraction isn't reliable: say so, don't guess."*
- **Acceptance:** precision on auto-accepted fields ≥ target (see 06-evaluation); every abstention shows its reason in the UI.
- **Priority:** M

### SK-B5 — Question/answer pairing
Link the submitted question text to the government's answer text and the decision within and across documents of the same affair.
- Produces the `question`, `answer`, `decision` triple with provenance for each leg.
- **Acceptance:** for gold-set affairs with known Q/A structure, pairing accuracy is reported per body.
- **Priority:** M

### SK-B6 — Actor extraction
Submitters, co-signatories, addressed body, respondent — with roles from the controlled vocabulary and (where present) party/canton attributes.
- Maps to Popolo `Person`/`Organization` where possible.
- **Acceptance:** per-field P/R reported on gold set; names verbatim-verified.
- **Priority:** M

### SK-B7 — Procedural history & dates
Ordered list of procedural events (submitted, answered, debated, decided, withdrawn...) with ISO dates and event-type vocabulary.
- Date normalisation across DE/FR/IT formats; source format preserved in provenance quote.
- **Acceptance:** date normalisation unit tests for all three languages; event ordering validated against gold set.
- **Priority:** M

### SK-B8 — Tables & annexes handling
Detect budget/data tables and annexes; store them as structured blocks attached to the affair (markdown/CSV) instead of forcing them through field extraction.
- **Acceptance:** tables present in output as labelled blocks with page provenance; no table content silently dropped or hallucinated into fields.
- **Priority:** S

### SK-B9 — Related-affair linking
Detect references to other affairs (IDs, titles, dates) and link them within the corpus.
- **Acceptance:** explicit references ("Motion 21.3456") resolved to internal IDs when present in corpus.
- **Priority:** C

### SK-B10 — Batch processing with resume & cost tracking
Queue-based batch extraction across the corpus; resumable after failure; per-document metrics logged (tokens, latency, CHF estimate, retries, abstain count).
- **Acceptance:** kill mid-batch → restart → no document processed twice, no document lost; cost report per batch.
- **Priority:** M

---

## C. Review Workbench

### SK-C1 — Side-by-side compare view
PDF (or page image) on the left; extracted fields on the right; text/Docling/JSON tabs. Mirrors OpenParlData's existing extraction workbench so the output drops into their production mental model.
- **Acceptance:** one screen shows source + all extracted fields without scrolling context away.
- **Priority:** M

### SK-C2 — Click-to-source highlighting
Clicking any extracted value scrolls to and highlights its provenance span in the source view (and vice versa).
- **Acceptance:** works for every field that has provenance; fields without provenance are visually marked as unverified.
- **Priority:** M

### SK-C3 — Accept / correct / reject per field
Reviewer can accept a value, edit it (edit keeps provenance + marks origin `manual`), or reject it to `null`. Document-level approve when all fields resolved.
- Full audit trail: who, when, old value, new value.
- **Acceptance:** corrections persist, update metrics, and export reflects them.
- **Priority:** M

### SK-C4 — Review queue
All documents needing attention, sorted by lowest field confidence; filter by body, language, affair type, reason code.
- **Acceptance:** a reviewer can clear the demo corpus queue using only the queue UI; queue count is visible on the dashboard.
- **Priority:** M

### SK-C5 — Extracted vs inferred vs manual labelling
Every value visually tagged by origin: `extracted` (verbatim-verified), `inferred` (model-derived, flagged), `manual` (human). Nothing silently mixed.
- **Acceptance:** origin labels visible per field and present in export JSON.
- **Priority:** M

### SK-C6 — Batch operations
Approve all auto-verified fields of a document, re-run extraction with a newer prompt/model version, bulk-assign.
- **Priority:** S

---

## D. Query & Answers

### SK-D1 — Structured query over extracted data
Filter/aggregate affairs across bodies: by type, submitter, party, topic keyword, date range, decision outcome, language.
- **Acceptance:** SQL/JSON query API returns correct counts against gold-set annotations.
- **Priority:** M

### SK-D2 — Cited answer generation
Natural-language question → Apertus answer composed **only** from verified extracted data; every sentence carries citations to affair + field + source span.
- Refuses to answer beyond the data ("not in the extracted corpus") rather than generalising.
- **Acceptance:** citation coverage = 100% of answer sentences; clicking a citation opens the compare view at the exact span.
- **Priority:** M

### SK-D3 — The killer query (demo)
One cross-parliamentary question that "can't currently be answered reliably", answered live from extracted data — e.g. *"Which municipalities asked the government about <topic> in the last year, and what was the answer?"*
- Pre-selected, rehearsed, with a recorded fallback video.
- **Acceptance:** runs offline against the cached corpus in < 10 s.
- **Priority:** M

### SK-D4 — Multilingual UI & answers
Query and answer in DE and FR minimum; extracted content stays in source language with on-demand Apertus translation (labelled `generated`).
- **Priority:** S

---

## E. Evaluation & Quality

### SK-E1 — Gold set builder
Tooling to annotate 30–50 documents (multi-body, multi-language, mixed born-digital/scanned) with field-level ground truth, stored in `data/gold/`.
- **Acceptance:** annotation format documented; inter-annotator spot check reported.
- **Priority:** M

### SK-E2 — Metrics harness
One command computes per-field precision/recall/F1, sliced by language, body, document type (digital/scanned); plus abstention rate, verification-failure rate, cost/latency stats.
- Outputs a markdown table straight into the README and technical report.
- **Acceptance:** `make eval` reproduces the published numbers from the committed gold set and run artefacts.
- **Priority:** M

### SK-E3 — Schema validator
Standalone validator (CLI + library) that checks any Skony JSON output: schema conformance, controlled vocabularies, date formats, provenance presence, Q/A/decision consistency rules.
- **Acceptance:** used in CI and by the batch pipeline; invalid docs can never reach export.
- **Priority:** M

### SK-E4 — Baseline comparison
Run two baselines on the same gold set: (a) Docling structure only, (b) unconstrained ad-hoc prompting. Skony must beat both on field F1 *and* on provenance coverage.
- **Acceptance:** comparison table in the technical report.
- **Priority:** S

---

## F. Export & Integration

### SK-F1 — OpenParlData-shaped export
Export approved extractions in a shape matching OpenParlData's API model, plus native Skony JSON with full provenance, plus CSV for spreadsheets.
- **Priority:** M

### SK-F2 — Standards mapping export
Optional serialisations: Popolo JSON for actors, Akoma Ntoso fragment mapping for structure, eCH-aligned field naming documented.
- **Priority:** C

### SK-F3 — Public REST API
Everything the UI does, available via the documented API (see [05-api](05-api.md)).
- **Priority:** M

---

## G. Operations & Sovereignty

### SK-G1 — One-command run
`make run` → Docker Compose builds and starts db + api + worker + ui, seeds the demo corpus, prints the URL. Works on a clean checkout, offline after image pull.
- **Acceptance:** a machine that never saw the repo is demo-ready in ≤ 5 min.
- **Priority:** M

### SK-G2 — Apertus-only LLM access
All LLM calls go through one client reading `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`. No other model provider in the dependency tree.
- **Acceptance:** repo-wide scan finds no other LLM SDK; swapping endpoint to a self-hosted 8B requires env vars only.
- **Priority:** M

### SK-G3 — Observability dashboard
Extraction counts, verification-failure rate, abstain rate, latency, token usage, CHF/doc — visible in the UI and logged as structured JSON.
- **Priority:** S

### SK-G4 — Self-host profile
Documented deployment on a ~20 GB RAM VPS (Apertus-8B local) and on CSCS/Phoeniqs endpoints (70B quality runs). No data leaves Swiss infrastructure.
- **Priority:** M

---

## Feature matrix (summary)

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| A1 | Corpus import | M | planned |
| A2 | Digital/scanned detection | M | planned |
| A3 | Language detection | M | planned |
| A4 | Layout segmentation | M | planned |
| A5 | Pre-cached demo corpus | M | planned |
| B1 | Schema-first extraction | M | planned |
| B2 | Provenance capture | M | planned |
| B3 | Hallucination guard | M | planned |
| B4 | Confidence & abstention | M | planned |
| B5 | Q/A pairing | M | planned |
| B6 | Actor extraction | M | planned |
| B7 | Procedural history | M | planned |
| B8 | Tables & annexes | S | planned |
| B9 | Related-affair linking | C | planned |
| B10 | Batch + cost tracking | M | planned |
| C1 | Compare view | M | planned |
| C2 | Click-to-source | M | planned |
| C3 | Accept/correct/reject | M | planned |
| C4 | Review queue | M | planned |
| C5 | Origin labelling | M | planned |
| C6 | Batch review ops | S | planned |
| D1 | Structured query | M | planned |
| D2 | Cited answers | M | planned |
| D3 | Killer query demo | M | planned |
| D4 | Multilingual UI | S | planned |
| E1 | Gold set builder | M | planned |
| E2 | Metrics harness | M | planned |
| E3 | Schema validator | M | planned |
| E4 | Baseline comparison | S | planned |
| F1 | OpenParlData export | M | planned |
| F2 | Standards export | C | planned |
| F3 | Public API | M | planned |
| G1 | One-command run | M | planned |
| G2 | Apertus-only client | M | planned |
| G3 | Observability | S | planned |
| G4 | Self-host profile | M | planned |
