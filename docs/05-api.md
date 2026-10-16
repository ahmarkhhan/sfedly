# 05 — REST API

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

FastAPI service, JSON everywhere, OpenAPI docs auto-generated at `/docs`. Base URL in dev/demo: `http://localhost:8080/api/v1`. All extraction payloads follow [03-data-model](03-data-model.md).

## Documents & ingestion

| Method | Path | Description |
|---|---|---|
| `POST` | `/documents/import` | Import from OpenParlData (`{source: "api"|"export"|"local", body_id?, limit?}`) — enqueue ingestion |
| `GET` | `/documents` | List documents. Filters: `body_id`, `language`, `kind` (digital/scanned), `status` |
| `GET` | `/documents/{id}` | Document detail: metadata, segments, pages, offset map availability |
| `GET` | `/documents/{id}/pages/{n}` | Page text (with offsets) or rendered page image (`?as=image`) |

## Extraction

| Method | Path | Description |
|---|---|---|
| `POST` | `/extractions` | Run extraction. Body: `{document_id, prompt_version?, model?}`. Async → returns job ID |
| `GET` | `/extractions/{job_id}` | Job status + result extraction ID when done |
| `GET` | `/extractions/by-document/{doc_id}` | Latest extraction (or `?version=all`) for a document |
| `GET` | `/extractions/{id}` | Full `ParliamentaryAffair` JSON with per-field provenance/confidence/origin |
| `GET` | `/extractions/{id}/provenance` | Flat span list for UI highlighting: `[{field_path, page, span, quote, status}]` |
| `POST` | `/extractions/{id}/rerun` | Re-extract with a different prompt/model version (keeps history) |

## Review

| Method | Path | Description |
|---|---|---|
| `GET` | `/review/queue` | Documents needing review, sorted by lowest field confidence. Filters: `body_id`, `language`, `reason`, `affair_type` |
| `POST` | `/review/{extraction_id}/fields/{field_path}` | `{action: "accept"|"correct"|"reject", value?}` — corrections keep provenance, set origin `manual`; append-only audit |
| `POST` | `/review/{extraction_id}/approve` | Approve document (all fields resolved) → exportable |
| `GET` | `/review/audit/{extraction_id}` | Full audit trail (who/when/old/new) |

## Query & answers

| Method | Path | Description |
|---|---|---|
| `POST` | `/query` | Structured query: `{filters: {affair_type?, body_id?, party?, date_range?, outcome?, q?}, aggregate?}` → matching affairs + counts |
| `POST` | `/ask` | Natural-language question → cited answer. Response: `{answer: [{sentence, citations: [{affair_id, field_path, page, span}]}], refusal: string|null}` |
| `GET` | `/affairs/{id}` | One affair, fully resolved (post-review state) |

## Schema, metrics, ops

| Method | Path | Description |
|---|---|---|
| `GET` | `/schema` | Current JSON Schema + vocabulary versions |
| `GET` | `/metrics` | Extraction counts, verification-failure rate, abstain rate, tokens, latency, CHF/doc |
| `GET` | `/eval/latest` | Latest evaluation report (per-field P/R/F1 × language × body) |
| `GET` | `/health` | Liveness/readiness (db, llm endpoint reachable) |

## Conventions

- **Errors:** RFC 7807 (`application/problem+json`) with stable `type` codes (`document_not_found`, `extraction_failed`, `validation_error`…).
- **Pagination:** `limit`/`offset`, default 50, max 500.
- **Versioning:** path prefix `/api/v1`; schema version inside payloads (`schema_version`).
- **Auth:** none in the hackathon demo (localhost); a `SKONY_API_TOKEN` header check is the documented production switch.
- **Idempotency:** extraction requests keyed by (document, prompt_version, model) — repeated `POST /extractions` returns the existing job.

## Example — cited answer

```http
POST /api/v1/ask
{"question": "Welche Gemeinden haben 2025 nach Wasserschutz gefragt und was wurde geantwortet?"}
```
```json
{
  "answer": [
    {"sentence": "Nidau und zwei weitere Gemeinden stellten 2025 Vorstösse zum Wasserschutz.",
     "citations": [{"affair_id": "743-2021-0142", "field_path": "question_text",
                    "page": 1, "span": [1330, 1488]}]},
    {"sentence": "Der Gemeinderat Nidau lehnte zusätzliche Messungen ab und verwies auf kantonale Programme.",
     "citations": [{"affair_id": "743-2021-0142", "field_path": "answer_text",
                    "page": 2, "span": [402, 561]}]}
  ],
  "refusal": null
}
```
