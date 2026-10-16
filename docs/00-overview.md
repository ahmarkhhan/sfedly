# 00 — Product Overview

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

## What is Skony?

Skony is a **conservative-extraction pipeline and review workbench** that converts heterogeneous Swiss parliamentary PDFs (motions, postulates, interpellations, written questions, initiatives) into one versioned, documented, common schema — with every value traceable to its source page and text span. On top of the extracted data, Skony answers **cross-parliamentary questions** where every sentence of the answer links back to the original document.

Built exclusively on **Apertus v1.5** (8B for iteration, 70B for quality runs). No external commercial APIs. Fully self-hostable on a ~20 GB RAM VPS or CSCS infrastructure.

## The problem

- OpenParlData scrapes **90 Swiss parliaments** daily and publishes **~300,000 parliamentary affairs** as open data — but the valuable *content* (the question asked, the government's answer and reasoning, the decision, the people involved) sits buried in PDFs.
- Documents are extremely heterogeneous: born-digital and scanned, stamped, signed, with tables and annexes, in **four languages** (DE/FR/IT/EN).
- Generic document AI (e.g. Docling) produces clean but domain-agnostic structure; ad-hoc LLM prompting produces a different JSON shape per parliament. Neither is traceable.
- There is no gold standard and no metric, so nobody can say whether an extraction pipeline is good enough to run unattended.

## The answer

Skony fills the missing **middle layer** (document structure *and* affair semantics) with three pillars:

1. **Schema-first core** — a versioned representation model for parliamentary affairs with controlled vocabularies, small enough for a municipality and expressive enough for national parliaments. Maps to Akoma Ntoso, Popolo, eCH (Fachgruppe Politische Geschäfte) and Docling where sensible.
2. **Apertus extractor with citations** — structured-output prompts; every field carries provenance (`page` + text `span` + verbatim `quote`). A verifier enforces that each value is literally findable in the source text, otherwise the field becomes `null` and the document is flagged for review.
3. **Human review + evidence** — a side-by-side PDF ↔ fields workbench (mirroring OpenParlData's production UX), plus an evaluation harness that reports precision/recall per field, per language, per parliament against a manually checked gold set.

## Users

| User | Need | Skony feature |
|---|---|---|
| OpenParlData operator (challenge owner) | Production-fit extraction feeding the existing workbench and API | Converter + validator + export in their API shape; same stack (Python/FastAPI/Pydantic/PostgreSQL) |
| Municipal / cantonal clerks | Trustworthy structured records without manual retyping | Review queue, accept/correct, abstention on low confidence |
| Journalists & researchers | Cross-parliamentary questions with proof | Query interface with sentence-level citations |
| Citizens | Understandable answers about parliamentary affairs | Cited plain-language answers (DE/FR demo) |

## Value proposition (mapped to the judging rubric)

| Criterion | How Skony scores |
|---|---|
| Purposeful use of AI | Solves a named partner pain (buried PDF content at 300k-doc scale), not a generic chat wrapper |
| Technical rigour | Gold-set evaluation, per-field metrics, honest error analysis, abstention policy |
| Value, cost & scalability | CHF/document cost tracking, batch pipeline, runs unattended with review-by-exception |
| Sovereign deployability | Apertus-only on Swiss infrastructure, Docker one-command run, zero external API calls |
| Implementation feasibility | Fits OpenParlData's production stack and 20 GB RAM VPS; schema mapped to emerging eCH standard |

## Scope

**Hackathon scope (18–19 Oct):** 3–5 parliamentary bodies across 2 languages (DE + FR), one killer cross-parliamentary query answered live, evaluation on a 30–50 document gold set.

**Explicitly out of scope:** all 90 parliaments, real-time scraping, speech/debate transcripts (that is Parla-CLARIN territory), legislative drafting (Akoma Ntoso's home ground), non-parliamentary document types.

## Success definition

Per the challenge brief, the main criterion is **insight**: *is a common schema for parliamentary affairs feasible — which parts generalise, and where do fundamental differences remain?* A convincing negative or partial answer counts as success. Skony's evaluation report is designed to deliver exactly that.

## Naming, license, links

- **Name:** Skony
- **License:** open source (event T&C §6) — Apache-2.0 intended
- **Template:** github.com/HackApertus/project-template (Track 2A directory kept as-is)
- **Data:** files.openparldata.ch/doc/ (PDFs + pre-extracted Tika/PDFBox text), api.openparldata.ch/v1/, bulk exports
- **Models:** huggingface.co/swiss-ai/Apertus-v1.5-8B, huggingface.co/swiss-ai/Apertus-v1.5-70B
