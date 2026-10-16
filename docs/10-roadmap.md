# 10 — Roadmap

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

## Phase 0 — Before the event (14–17 Oct)

- [ ] Fork HackApertus/project-template; keep `track_2a/`, delete others
- [ ] Docker skeleton: compose with db/api/worker/ui + `make run` printing a health URL
- [ ] `src/llm/client.py` reading `LLM_NAME` / `LLM_BASE_URL` / `LLM_API_KEY`, smoke-tested against the event endpoint
- [ ] Download Apertus-8B weights; test the `local-llm` offline profile
- [ ] Pre-fetch corpus sample: 3–5 bodies, DE+FR, mixed digital/scanned → `data/corpus/` (≤100 MB with gold set)
- [ ] Pydantic schema v1 + vocabularies + validator with unit tests
- [ ] Prompt v0.1 (DE/FR) for the five affair types
- [ ] Verifier v1 (exact/normalised/fuzzy matching) with seeded-hallucination tests
- [ ] Pitch skeleton + cost-sheet slide template + demo fallback recording plan
- [ ] Verify registrations: sprintd + Luma + Discord

## Phase 1 — Day 1 (Sat 18 Oct)

| Time | Action |
|---|---|
| 08:00 | Doors; set up; test venue network, then assume it dies |
| 09:00 | Challenge pitches — confirm OpenParlData case details vs assumptions |
| 09:30 | **Cases unlock.** First hour: map the actual case onto the pre-built skeleton; freeze scope (bodies, languages, killer query) |
| 11:30 | Hacking starts |
| 11:30–14:00 | Ingestion + segmentation on real corpus; gold set annotation begins (10 docs) |
| 14:00–18:00 | Extraction loop live end-to-end; verifier wired; first real numbers |
| 18:00–21:00 | Compare view + click-to-source; gold set to 30 docs; first `make eval` table |
| 21:00 | Book mentors (Pedregosa / Lavrovsky especially) for day-2 morning |

## Phase 2 — Day 2 (Sun 19 Oct)

| Time | Action |
|---|---|
| 08:00–10:00 | Review queue + accept/correct; cited-answer endpoint; killer query working offline |
| 10:00–11:00 | Mentor sessions; fold feedback into pitch, not into scope |
| 11:00–12:30 | **Feature freeze 12:30.** Final 70B quality run; final eval; baselines table |
| 12:30–14:00 | README, technical_report.md (numbers inlined), license, clean-VM `make run` test, fallback video |
| **14:30** | **Submission** |
| 15:00–16:45 | Partner pitches = the real Top-6 audition |
| 18:30–19:10 | Finals: 4-minute choreography from [08-ui-ux](08-ui-ux.md) |

## Phase 3 — After the event

- **Handover to OpenParlData**: align export shape with their admin workbench; propose schema findings to the eCH Fachgruppe Politische Geschäfte (the insight deliverable has a real audience).
- **Gold set v2**: 200+ docs, more bodies, IT included; inter-annotator agreement study.
- **Corpus scale run**: batch over the 300k corpus on the VPS profile; publish cost/coverage report.
- **Series continuity**: Liebefeld winner qualifies for the Grand Finals (14 May 2027, St.Gallen) — harden deployment, grow the gold set, keep the repo public and active.

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Venue network failure | high | fully offline demo profile; cached corpus; fallback video |
| Case differs from assumptions | medium | skeleton is case-agnostic; first-hour mapping slot; scope knife ready |
| 8B quality too weak on FR | medium | 70B for scored runs; per-language honesty slide |
| Gold set too small for credible stats | medium | annotate early (day-1 afternoon), stratify hard cases |
| Time sink in UI polish | high | UI non-goals list (08); keyboard flow only |
