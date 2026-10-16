# 🏛️ Skony — parliamentary data with proof

> **Apertus proposes. Evidence disposes.**
> Skony turns parliamentary PDFs into searchable, source-linked records: Apertus 1.5
> suggests structured fields, and a person verifies each one against the original page
> before it enters a reviewed export.

![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Tests](https://img.shields.io/badge/tests-247%20Python%20%2B%2016%20UI%20passing-brightgreen)
![Docker](https://img.shields.io/badge/docker-6%2F6%20checks%20passing-blue)
![Languages](https://img.shields.io/badge/languages-DE%20%C2%B7%20FR%20%C2%B7%20IT%20%C2%B7%20RM%20%C2%B7%20EN-orange)

**Hack Apertus online hackathon** (CSCS, Track 2A — OpenParlData) · Final submission 16 October 2026 · Apache-2.0

---

## 💡 What it does — 30-second intro

- **The problem:** parliaments publish decisions as PDFs — hard to search, compare, or reuse. Pure LLM extraction hallucinates; pure manual work doesn't scale.
- **The answer:** every extracted field carries a **verbatim quote + page number** from the source PDF. Unreviewed suggestions **never** reach an export.
- **The payoff:** researchers get cited, filterable dossiers in seconds; reviewers get one-click evidence inspection; everyone gets a full audit trail.
- **One prompt, five languages:** German, French, Italian, Romansh, English.

## 🚀 Quickstart — running in ~5 minutes

**Prerequisites**

- Docker Engine / Docker Desktop (Linux containers) + **Compose v2** with `up --wait`
- GNU Make (only for the shortcut) · port `8765` free · internet for the first image build
- **Not needed:** API key, GPU, model weights, local Python, Poppler (all in the image)

**Run it**

```bash
git clone https://github.com/ahmarkhhan/sfedly.git
cd sfedly
make run
```

Then open **http://localhost:8765** and try the built-in **replay demo** — a synthetic
practice document with recorded model output, fully offline.

**Useful commands**

| Command | Effect |
| --- | --- |
| `make run` | Build image, start workbench on `:8765` |
| `make test` | Full test suite inside the container |
| `make logs` | Follow server logs |
| `make down` | Stop (uploads, reviews, audit history survive in the `review-state` volume) |
| `make verify-docker` | 6-gate Docker check (build, tests, health, non-root, persistence, cleanup) |
| `SKONY_PORT=9000 make run` | Use a different host port |

**Live extraction with Apertus (optional):** put your CSCS endpoint + API key in
`track_2a/.env` (see `track_2a/.env.example`), then upload a real parliamentary PDF.
Details: [Docker running guide](track_2a/docs/RUNNING.md).

## ⚙️ How the components work

```
 Parliamentary PDF  (DE · FR · IT · RM · EN)
        │
        ▼
 ┌─[1] CONVERT ── pdf.py
 │      PDF → per-page text and images
 │      ▼
 ├─[2] EXTRACT ── pipeline_v2.py + src/prompts/extract.txt
 │      Apertus 1.5 suggests typed fields; every value carries
 │      a verbatim quote + page number as evidence
 │      ▼
 ├─[3] VALIDATE ── schema.py · contracts.py · completeness.py · verify.py
 │      type & contract checks, completeness gates, replay-fixture verification
 │      ▼
 ├─[4] HUMAN REVIEW ── workbench at http://localhost:8765
 │      /         confirm or correct fields beside the original PDF page
 │      /explore  search dossiers across parliaments, follow citations
 │      /scoped   snapshot a scope, compare accepted evidence offline
 │      every decision is saved with an audit trail
 │      ▼
 └─[5] REVIEWED-ONLY EXPORT ── cited JSON / CSV briefs
        state persists in the Docker `review-state` volume
```

- **No evidence, no field:** the validator rejects records without verbatim page/quote support.
- **Human gate:** extraction output is a *suggestion*; only reviewed values are exported.
- **Replayable:** recorded model responses let anyone verify the pipeline with zero model calls.

## 🖥️ The three screens

| Screen | What to try | What it demonstrates |
| --- | --- | --- |
| **Review documents** · `/` | Open a document, select a field, inspect its supporting passage. | Human review beside the original PDF, saved decisions, audit trail. |
| **Explore affairs** · `/explore` | Search the collection, open a dossier, follow a citation. | Research across source text, requests, answers, events, signatories. |
| **Compare evidence** · `/scoped` | Review a source scope, save a snapshot, compare wording. | Explicit review boundaries and a fixed, immutable record of accepted evidence. |

## 🧩 Key components (submission checklist)

- **PDF-to-schema converter** — [pdf.py](track_2a/src/skony/pdf.py) (PDF → page text) feeding [pipeline_v2.py](track_2a/src/skony/pipeline_v2.py) into the typed record model in [schema.py](track_2a/src/skony/schema.py).
- **Apertus prompts** — [src/prompts/extract.txt](track_2a/src/prompts/extract.txt): the Apertus 1.5 extraction prompt (DE/FR/IT/RM/EN) with verbatim page/quote evidence rules.
- **Validator** — schema/contract checks in [schema.py](track_2a/src/skony/schema.py) + [contracts.py](track_2a/src/skony/contracts.py), extraction-completeness in [completeness.py](track_2a/src/skony/completeness.py), replay verification in [verify.py](track_2a/src/skony/verify.py).
- **Samples** — [track_2a/data/sample](track_2a/data/sample): synthetic practice PDF + expected JSON + checksum manifest, runnable offline via the replay demo.
- **Batch extraction** — per-row checkpoints, preserved failures, exact-request caching: a real DE/FR pair replayed with **2 cache hits, 0 model calls**; 12 prior field decisions preserved.
- **Gold set** — frozen gold v1: four fully human-reviewed documents (DE municipal, FR cantonal), published with manifest for reproducibility.

## ✅ Status & honest limits

**Verified working**

- ✅ Real CSCS pilot completed; live extraction against Apertus on CSCS infrastructure.
- ✅ Review workbench: original pages, source checks, persistent corrections, audit history, reviewed-only exports — persistence survives container rebuilds.
- ✅ Docker image passed the full build/run check on 16 Oct 2026 (image build, in-container tests, health + PDF/image preview, non-root runtime, review-state persistence, disposable cleanup).
- ✅ **247 Python engineering tests + 16 interface-controller tests** green (16 October 2026).
- ✅ v0.2 contracts at `/scoped`: dependency-aware scoped review, immutable offline comparison, legacy migration, gold eligibility/scoring, capability-based citations.

**Not claimed**

- ⚠️ Gold v1 is **small, single-annotator, in-sample** — it measures development-set self-consistency, **not** generalisation.
- ⚠️ Corpus-level model accuracy remains **unmeasured**.
- ⚠️ A located passage is **evidence to inspect, not automatic proof** that a field is correct.
- ⚠️ The main extraction screen still uses v0.1 contracts; new checks are synthetic.

## 🔭 What's next — future features

> **Roadmap only.** Everything below is post-hackathon design intent — none of it is
> an implemented capability or a measured result today.

Skony's architecture is built to grow along four axes. **First, scale the evaluation:** expand the frozen gold set from four single-annotator documents to a multi-annotator, cross-parliament corpus, so per-field and cross-language accuracy can finally be measured rather than assumed — the pipeline already exposes the eligibility and scoring hooks for it. **Second, broaden coverage:** extend the record schema beyond request/answer affairs to motions, votes, and committee reports, and onboard additional cantonal and municipal bodies through the existing affair-type mapping layer. **Third, deepen the tooling:** migrate the main extraction screen from v0.1 to the v0.2 contracts, add batch review queues with inter-annotator agreement metrics, and ship a public read-only API over the reviewed export so researchers can query cited records programmatically. **Fourth, harden the evidence loop:** automatic re-verification of stored citations when source PDFs are re-published, drift detection across extraction runs, and confidence-ranked field suggestions so reviewers spend time where the model is least sure. Each of these lands as a validated contract extension — with the same rule that holds today: nothing enters an export without evidence and a human decision behind it.

## 📁 Repository layout

```
sfedly/
├── Makefile             # make run / test / down / logs / verify-docker
├── PROJECT_IDEA.md      # earlier project idea and phased build plan
├── docs/                # direction, source register, research, pilot write-ups
└── track_2a/            # ← active challenge code (server, pipeline, prompts, tests, data)
    ├── src/skony/       # pdf.py · pipeline_v2.py · schema.py · contracts.py · …
    ├── src/prompts/     # extract.txt (Apertus 1.5, 5 languages)
    ├── data/            # sample (synthetic, offline) · gold (frozen v1)
    └── docs/            # RUNNING · DEVELOPMENT · BUILD_STATUS · verification guides
```

> The active challenge directory is `track_2a/`. Earlier Liebefeld material is
> **historical planning**: its broad feature lists and illustrative targets are
> not implemented capabilities or measured results.

## 📚 Documentation

**Start here**

- [Authoritative project direction and requirements](docs/16-project-direction.md)
- [Current implementation status](track_2a/docs/BUILD_STATUS.md)
- [Run and update the Docker/replay version](track_2a/docs/RUNNING.md)
- [Run extraction and the review workbench](track_2a/docs/DEVELOPMENT.md)
- [Active technical report draft](track_2a/technical_report.md)

**Evidence and limits**

- [Source register and verification limits](docs/17-source-register.md)
- [Verified pipeline results and remaining limits](track_2a/docs/PIPELINE_VERIFICATION.md)
- [First live CSCS pilot](docs/12-cscs-pilot.md)
- [A1–A7 contracts, scoped review and verification](track_2a/docs/AUDIT_IMPLEMENTATION.md)
- [Batch extraction, replay and review import](track_2a/docs/BATCH_EVALUATION.md)
- [Public data, synchronization and secret handling](track_2a/docs/PUBLICATION.md)
- [Website review and corrected requirements](docs/11-online-research.md)
- [Delivery backlog and release gates](docs/18-delivery-backlog.md)

---

An Apertus 1.5 project for the **Hack Apertus online hackathon**, ending 16 October 2026 at 12:00 CEST / 15:00 Pakistan time. Released under the [Apache-2.0 license](LICENSE).
