# 13 — Online Sprint Plan (14 → 16 Oct 2026)

> Superseded on 15 October by [project direction](16-project-direction.md) and
> [delivery backlog](18-delivery-backlog.md). The schedule, larger sample counts,
> confidence setting and replay-mode configuration below are historical targets,
> not confirmed runtime features or official minima. The updated plan also
> expands cache identity and separates semantic correctness from token overlap.

*Written 14 Oct 2026, 09:00 PKT. Supersedes the Liebefeld day-plan assumptions in [10-roadmap](10-roadmap.md) for the **online** phase.*

## 0. Facts that shape the plan

| Fact | Value |
|---|---|
| Deadline | **Fri 16 Oct 2026, 12:00 CEST = 15:00 PKT** (no extension, per rules) |
| Now | Wed 14 Oct, 09:00 PKT → **~54 h remaining** |
| Submission channel | https://hackapertus.ch/online-hack/submissions (**not** Devpost) |
| Submission form | Public repo from `HackApertus/project-template`; technical report PDF **≤ 6 pages**; repo contains converter + prompts + validator + README with samples |
| Judging (Track 2A) | **Insight** (is a common schema feasible? partial/negative answers count) + **Breadth & applicability** across parliaments/types/languages |
| Deliverables (deck) | D1 representation model · D2 converter w/ provenance · D3 evidence (gold-set eval + ≥1 cross-parliamentary question answered) |
| Done already | CSCS endpoint live (`api.inference.cscs.ch/v1`); 70B pilot on 1 PDF; strict schema v1; quote→span verifier; abstention; 21 tests; CLI; `server.py` stub |
| Known gap | 8B failed strict validation (raw-v0.1/v0.2 rejected); 70B passed → 70B is the scored model; the 8B gap is itself a reportable insight |

### The three things the jury will check
1. `make run` works on a clean checkout → review UI opens, seeded corpus, **works without an API key** (replay mode).
2. The technical report answers the insight question with measured numbers (P/R/F1, abstention, per-language/per-body slices, baseline comparison).
3. The repo demonstrates conservative extraction: provenance on every value, abstention instead of guesses, a working human-review loop.

---

## 1. Scope for the online submission (cut hard, no exceptions)

**IN**
- Corpus: **24–30 PDFs, 4–5 bodies, DE + FR, mixed born-digital/scanned** (files.openparldata.ch exports, licence-checked, source manifest + SHA-256 digests)
- Pipeline: intake → Apertus 70B structured extraction (frozen prompt version) → verifier → abstention → store (**JSONL + SQLite**, not PostgreSQL — sprint cut; report notes the production mapping)
- Gold set: **≥ 20 human-annotated documents**, field-level with spans; separate **dev slice ≥ 6 docs** for prompt tuning (gold never appears in prompts)
- Eval harness: deterministic scorer, metrics table, one baseline (ad-hoc unconstrained prompt), `make eval`
- Review UI: **one server-rendered page** (FastAPI + Jinja or static HTML+JS, no build step): queue list → side-by-side extracted JSON vs. source page text with the span highlighted → accept / correct / reject → append-only audit log
- Cross-parliamentary question (D3): answered **from verified extractions as a structured query** (no RAG), e.g. *"Which bodies debated ‹topic›, who submitted, what was decided?"* → table with (doc, page, span) citations. `make question`
- Docker: single image + `Makefile` (`run` / `test` / `eval` / `question`) + `.env.example`
- Technical report PDF ≤ 6 pages + README with samples

**OUT (listed as future work in the report; do not build)**
- Free-form cited Q&A / RAG (SK-D) · PostgreSQL · local-llm 8B offline profile · Tesseract OCR · multi-user auth · React build · IT language · long-doc chunking (log-only) · runtime ingestion from the live OpenParlData API

---

## 2. Technical requirements

### 2.1 Machine & OS
- Dev: Windows + PowerShell, Docker Desktop (Linux containers), Python 3.11+.
- `make` on Windows via `winget install GnuWin32.Make` or chocolatey; README also documents the raw `docker compose` equivalents so judges on any OS can run without make.
- Judge machine assumed: clean Docker, **possibly no CSCS key, possibly no internet** → replay mode (§3 B3) is mandatory.

### 2.2 Accounts & endpoints
- CSCS Inference: `LLM_BASE_URL=https://api.inference.cscs.ch/v1`, bearer key from the hackathon email (local `.env` only).
- Models: `LLM_NAME=swiss-ai/Apertus-v1.5-70B` (scored runs); `swiss-ai/Apertus-v1.5-8B` (comparison / failure analysis only).
- Data: `https://files.openparldata.ch/exports/` and `…/doc/` (PDFs + pre-extracted Tika text).
- Submission form: hackapertus.ch/online-hack/submissions. Blockers → info@openparldata.ch (Christian Gutknecht) or Discord.

### 2.3 Environment contract (already implemented — keep exactly)
`LLM_NAME` / `LLM_BASE_URL` / `LLM_API_KEY`, plus `SKONY_DATA_DIR` (default `./data`), `SKONY_CONFIDENCE_THRESHOLD` (default `0.85`), `SKONY_MODE=replay|live` (default `replay`).

### 2.4 Repo hygiene (30 min, do FIRST)
- [ ] **Delete `track_2a/ (2).env`** (stray copy); search git history for leaked keys (`git log -p | Select-String` / `git grep`); rotate the CSCS key if anything was ever committed.
- [ ] `.gitignore` covers `.env`, `output/`, `tmp/`, unselected PDFs.
- [ ] `data/` ≤ 100 MB total (corpus + gold + cached LLM responses).
- [ ] LICENSE (Apache-2.0) present; README states corpus licence (parliament-published material) and redistribution basis.

---

## 3. Phase plan — steps, checks, tests

Times **PKT (CEST = PKT − 3h)**.

### PHASE A — Wed 14 Oct: corpus, gold set, batch pipeline

**A0 · Confirm submission requirements — 09:00–09:45 (06:00–06:45)**
- Re-read the Notion Getting Started Guide Track-2A section; open the submission form; write every required field into `docs/SUBMISSION.md`.
- ✅ **Gate G0:** `SUBMISSION.md` lists all required artefacts; nothing unknown.

**A1 · Corpus acquisition — 09:45–12:00 (06:45–09:00)**
- Bodies: e.g. Nidau (municipal, DE), canton Bern (DE), canton Fribourg/Vaud (FR), Federal Assembly (DE+FR) → 3 levels × 2 languages.
- `scripts/fetch_corpus.py`: download PDF + Tika text from a hand-picked list; write `data/corpus/manifest.jsonl` (source URL, export ID, retrieval time, SHA-256, body, language, doc-kind guess). Idempotent, digest-checked, committed.
- ✅ Check: `python -m skony manifest --check` → digests verify; count ∈ [24,30]; each language ≥ 8 docs; ≥ 3 bodies; ≥ 4 scanned/image-heavy docs.
- 🧪 `tests/test_manifest.py`: digest check fails on byte flip; duplicate IDs rejected.

**A2 · Gold-set annotation — 13:00–19:00 (10:00–16:00)** ← long pole, protect this block
- 20 gold docs stratified (bodies × languages × digital/scanned × affair types) + 6–8 **different** dev docs.
- `scripts/annotate.py`: renders page text, lets you fill schema JSON + your spans per field, saves `data/gold/<doc_id>.json`.
- Illegible/absent fields = `null` + reason. Gold abstentions are valid annotations.
- ✅ Check: 20 gold files pass schema validation; dev/gold disjoint (asserted).
- 🧪 `tests/test_gold.py`: all gold files validate; no dev/gold overlap.

**A3 · Batch extraction with caching — 15:00–20:00 (12:00–17:00), interleaved with A2**
- `scripts/run_batch.py`: per doc → intake → prompt build → CSCS call (70B, guided JSON as in pilot) → validate → verify → `output/runs/<doc_id>.json`; raw responses cached in `output/llm_cache/<hash>.json` (key = doc hash + prompt version + model).
- Concurrency 2, exponential backoff, **cache-first** (re-runs are free). Tokens/latency per call → `output/runs/_stats.jsonl` (feeds the cost table).
- ✅ **Gate G1:** ≥ 5 docs (incl. 1 FR, 1 scanned) flow end-to-end; every non-null field has a resolved span; abstentions carry reason codes.
- 🧪 `tests/test_pipeline_batch.py`: two runs over the same corpus produce identical outputs; the second makes **zero** HTTP calls (mock counter).

**A4 · Prompt iteration on the dev slice only — 20:00–23:00 (17:00–20:00)**
- Fix failure classes (FR date formats, multi-submitter lists, scanned headers). Bump `prompt_version` per change; one-line changelog per version in `src/prompts/CHANGELOG.md`.
- **Prompt freeze 23:00 PKT.** The final scored run uses the frozen version.
- ✅ Check: frozen version string present in every output record.

### PHASE B — Thu 15 Oct: eval, review UI, Docker

**B1 · Scored run on gold + eval harness — 09:00–12:00 (06:00–09:00)**
- `src/skony/scorer.py`: deterministic extraction↔gold comparison (exact/normalised for typed fields, token-F1 for free text) → P/R/F1, abstention by reason, provenance coverage, per-language and per-body slices.
- `make eval` writes `docs/eval/report.md` in the format from [06-evaluation](06-evaluation.md).
- Baseline: `scripts/run_baseline.py` — one generic "extract everything as JSON" prompt, no schema/vocab/verification, same gold, same scorer. Expected: shape drift + invented values (the failure mode the deck warns about).
- ✅ **Gate G2:** report with real numbers; baseline row present; provenance coverage asserted = 100%.
- 🧪 `tests/test_scorer.py`: handcrafted TP/FP/FN cases yield expected P/R/F1; scorer errors on missing provenance.

**B2 · Review UI — 13:00–18:00 (10:00–15:00)**
- Extend `server.py`: `GET /` queue table; `GET /review/{doc_id}` (left: fields + confidence + reasons; right: page text, resolved span highlighted); `POST /review/{doc_id}` accept/correct/reject → append `data/review/audit.jsonl`, update status.
- Server-rendered, no npm, no build step. Keyboard shortcuts (a=accept, n=next).
- ✅ Check: review one full document start-to-finish in < 2 minutes; audit log records who/what/when plus before→after diff.
- 🧪 `tests/test_api.py`: queue listing, review POST updates status + audit, rejected docs leave nothing marked verified.

**B3 · Docker + replay mode — 18:00–22:00 (15:00–19:00)**
- One `Dockerfile` (python:3.12-slim): installs deps, copies `src/`, `data/` (corpus + gold + **committed cached LLM responses**), exposes 8000.
- `make run` → `docker compose up` → `http://localhost:8000` with the review queue populated from cached outputs. `SKONY_MODE=replay` (default) serves everything from cache → **zero network, zero API key**. `SKONY_MODE=live` uses `LLM_*`.
- ✅ **Gate G3:** from a **fresh clone in a new directory** (simulates judge): `make run` serves the UI in < 5 min; `make test` passes inside the container; `make eval` reproduces the committed numbers from cached responses byte-identically.
- 🧪 `tests/test_replay.py`: replay mode with network disabled produces identical outputs (hash-compare).

**B4 · Cross-parliamentary question (D3) — 22:00–24:00 (19:00–21:00)**
- Pick the question from the verified extractions (choose the topic with best coverage, e.g. energy, housing, transport). `scripts/answer_question.py`: query SQLite over verified extractions → table: body / affair / submitter / decision / citation (doc, page, span). Render to `docs/eval/cross_parliamentary_answer.md` + a UI route.
- ✅ Check: every row's citation resolves to a verified span; ≥ 3 bodies represented; answer states corpus scope honestly.

### PHASE C — Fri 16 Oct: numbers, package, submit (hard stop 15:00 PKT)

**C1 · Final report — 09:00–11:00 (06:00–08:00)**
- Fill every ⟨placeholder⟩ in `technical_report.md` from `docs/eval/report.md`; write Section 5 (insight: what generalises / partially / breaks) from the measured slices; top-10 error analysis; cost table from `_stats.jsonl`.
- Export PDF ≤ **6 pages** (hard limit).
- ✅ **Gate G4:** report has zero placeholders; every number traceable to `make eval` output at the pinned commit.

**C2 · Clean-room verification — 11:00–12:30 (08:00–09:30)**
- Fresh clone → `make run`, `make test`, `make eval` (timed, notes in SUBMISSION.md). Walk the README exactly as written. Click through the UI: queue → review → question page.
- Fix only blockers. **Feature freeze was Thu 24:00 — docs and packaging only.**

**C3 · Submit — 12:30–14:00 (09:30–11:00)** *(buffer: 2 h before the 15:00 PKT deadline)*
- Repo public; final commit pushed; submit the form per `SUBMISSION.md`; save the confirmation (screenshot + any email) to `docs/SUBMISSION.md`.
- ✅ Done. Stop. No "one last fix".

---

## 4. Test plan (summary)

| Layer | Tests | When |
|---|---|---|
| Unit | existing 21 (schema, evidence, OCR-corruption abstention, client) + `test_manifest`, `test_gold`, `test_scorer` | every commit |
| Integration | `test_pipeline_batch` (cache determinism, zero-HTTP second run), `test_api` (review flow + audit), `test_replay` (offline replay identical) | phases A3/B2/B3 |
| Gates | G0 submission reqs · G1 end-to-end ≥5 docs · G2 eval numbers exist · G3 clean-checkout `make run` <5 min · G4 report complete | as marked |
| Adversarial | seeded-hallucination fixtures (invented value, wrong page, ambiguous quote, OCR garbage) — must all abstain, never pass | keep green from pilot |
| Honesty | gold never in prompts; dev/gold disjoint; frozen prompt version pinned in outputs; per-language numbers shown even when bad | report review |

**Pre-registered targets** (commitments, from [06](06-evaluation.md)): auto-accept precision ≥ 0.95 · provenance coverage 100% · seeded-hallucination catch 100% · typed-field F1 ≥ 0.90 · free-text F1 ≥ 0.75. Missed targets are reported, not hidden — the criteria reward honest insight.

---

## 5. Risk register

| Risk | L | Mitigation |
|---|---|---|
| Gold annotation overruns | H | hard timebox A2; drop to 15 gold docs before dropping stratification |
| CSCS rate limits/outage | M | cache-first everywhere; replay mode decouples packaging from the API; 8B comparison already have saved raw responses |
| Docker build slow on Windows | M | build image Thu evening, not Fri morning; single-stage slim image; pre-pulled base |
| Scope creep into Q&A/RAG | H | OUT list is final; "future work" section of the report absorbs ideas |
| Submission form surprise | M | A0 first; SUBMISSION.md; submit 2 h early |
| Secret leak in repo | L | 2.4 checklist + `git grep` before going public |
| 8B looks bad | — | not a risk: it is a measured, honest finding (structured-output reliability gap → why verification is mandatory) |

## 6. Cut list (explicit non-goals — already agreed in §1)

RAG/free-form Q&A · PostgreSQL · offline 8B serving · OCR · auth · IT language · live API ingestion · any UI polish beyond "readable and fast".

*If a block finishes early, the only legal pulls from the backlog are: (1) more gold docs, (2) Docling-only baseline, (3) page images in the review UI. In that order.*
