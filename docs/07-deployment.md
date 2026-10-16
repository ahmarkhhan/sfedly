# 07 — Deployment & Operations

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

## Judge quickstart (the only section that matters at 15:00)

```bash
git clone <repo> && cd <repo>/track_2a
make run
# → builds images, starts db+api+worker+ui, seeds the demo corpus
# → prints: UI at http://localhost:3000 · API at http://localhost:8080/docs
```

Requirements: Docker + Docker Compose, ~8 GB free RAM. No internet needed after image pull (demo corpus and gold set are in `data/`, ≤ 100 MB). LLM access is configured via env vars; a dockerised Apertus-8B profile is included for fully offline demos.

## Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `LLM_NAME` | yes | — | e.g. `Apertus-v1.5-8B` / `Apertus-v1.5-70B` |
| `LLM_BASE_URL` | yes | — | OpenAI-compatible endpoint (self-hosted, CSCS, Phoeniqs) |
| `LLM_API_KEY` | yes | — | `local` accepted for self-hosted |
| `DATABASE_URL` | no | compose-internal | external Postgres supported |
| `SKONY_DATA_DIR` | no | `./data` | corpus + artefact root |
| `SKONY_CONFIDENCE_THRESHOLD` | no | `0.85` | auto-accept threshold |

`.env.example` documents all of them; secrets never enter the repo.

## Docker Compose services

| Service | Image/build | Purpose |
|---|---|---|
| `db` | postgres:16 | affairs, extractions, audit, gold, metrics |
| `api` | ./Dockerfile | FastAPI on :8080 |
| `worker` | ./Dockerfile | ingest/extract/verify queue |
| `ui` | ./Dockerfile | workbench + query UI on :3000 |
| `llm` *(profile `local-llm`)* | vllm/ollama-class runtime | optional in-repo Apertus-8B for offline demos |

`make` targets: `run` (up + seed), `eval`, `test`, `seed`, `down`, `logs`.

## Deployment profiles

### A. Laptop / judge machine
Compose as above; point `LLM_BASE_URL` at the event endpoint or the `local-llm` profile.

### B. Sovereign VPS (OpenParlData-scale)
- Single VPS, ~20 GB RAM: Postgres + API + worker + UI + self-hosted Apertus-8B (quantised).
- No external calls at runtime — all data stays on Swiss soil; TLS via Caddy; nightly pg_dump.
- This is the profile that matches the challenge owner's actual infrastructure — production-fit by design.

### C. Quality mode (CSCS / Phoeniqs)
Same deployment, `LLM_BASE_URL` → Swiss-hosted 70B endpoint. Used for scored evaluation runs and hard documents. Fallback to 8B is one env var away.

## Cost sheet (template — fill with measured numbers from `make eval`)

| Item | 8B self-hosted | 70B endpoint |
|---|---|---|
| Infra | VPS ~CHF 40/mo (flat) | per-token, measured |
| Per document | ~CHF 0.0x | ~CHF 0.xx |
| 300k-doc corpus extrapolation | compute-bound, ~x weeks single node | CHF x,xxx one-off |
| Human review (10% abstain, 2 min/doc) | — | — |

Honest extrapolation is part of the pitch (value/cost/scalability criterion).

## Operations

- **Migrations:** Alembic, run automatically on `make run`.
- **Logs:** structured JSON to stdout; `make logs` tails all services.
- **Backups:** `pg_dump` + `data/` sync; restore documented in one command.
- **Health:** `/api/v1/health` checks db + LLM reachability; compose healthchecks gate startup order.
- **Updates:** schema/prompt versions are data, not deploys — rollouts are re-runs with a new version tag, old extractions retained.

## Clean-checkout checklist (run before submission)

1. Fresh machine/VM, clone, `make run` ≤ 5 min to working demo.
2. Demo works with venue-grade Wi-Fi **off** (local-llm profile or cached extractions).
3. `make eval` reproduces the README table from committed artefacts.
4. `make test` green (verifier + validator unit tests).
5. `technical_report.md` numbers match the eval output exactly.
