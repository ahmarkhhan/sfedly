# 03 — Data Model

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

The schema is the product. It is versioned (`skony.schema.v1`), documented, and enforced everywhere (extractor, validator, API, export). Small enough for a municipality, expressive enough for national parliaments.

## Design rules

1. **Every value is a cell, not a scalar.** A field = value + provenance + confidence + origin.
2. **Controlled vocabularies** for anything categorical — free text only where the source is free text.
3. **Null is a first-class citizen.** Missing/unreliable ⇒ `null` + reason, never a guess.
4. **The PDF is authoritative.** `inferred` values exist but are labelled and excluded from auto-accept.

## Core entity: `ParliamentaryAffair`

```python
class Field[T]:                    # every extracted attribute
    value: T | None
    provenance: Provenance | None  # required iff value came from a document
    confidence: float              # 0..1, set by the verifier
    origin: "extracted" | "inferred" | "manual"
    status: "auto_verified" | "needs_review" | "reviewed" | "rejected"
    abstain_reason: str | None     # low_confidence | span_not_found |
                                   # conflicting_sources | illegible_scan

class Provenance:
    document_id: str
    page: int                      # 1-based
    span: tuple[int, int]          # char offsets into that page's text
    quote: str                     # verbatim source substring
    bbox: tuple[float, float, float, float] | None  # when layout info exists

class Actor:
    name: Field[str]
    role: Field[ActorRole]         # vocabulary below
    party: Field[str] | None
    canton: Field[str] | None

class ProceduralEvent:
    event_type: Field[EventType]
    date: Field[date]              # ISO; source format kept in provenance.quote
    description: Field[str] | None

class ContentBlock:                # tables, annexes (SK-B8)
    kind: "table" | "annex" | "figure"
    label: Field[str] | None
    content_markdown: str | None
    provenance: Provenance

class ParliamentaryAffair:
    # identity & source
    affair_id: str                 # OpenParlData ID when present
    schema_version: str            # "skony.schema.v1"
    body_id: Field[str]            # parliament/council identifier
    body_name: Field[str]
    level: Field[Level]            # federal | cantonal | municipal
    language: Field[Language]      # de | fr | it | en | other
    source_url: str | None

    # semantics
    affair_type: Field[AffairType]
    title: Field[str]
    submitters: list[Actor]
    addressed_body: Field[str]     # who must answer (e.g. Gemeinderat, Conseil d'État)
    question_text: Field[str]      # the question as asked
    answer_text: Field[str]        # the executive's answer & reasoning
    decision: Field[DecisionOutcome]
    decision_date: Field[date]
    procedural_history: list[ProceduralEvent]
    related_affairs: list[str]     # affair_ids or unresolved references
    content_blocks: list[ContentBlock]

    # extraction metadata
    extraction: ExtractionMeta

class ExtractionMeta:
    model_name: str                # = LLM_NAME used
    prompt_version: str
    extracted_at: datetime
    document_status: "auto_verified" | "needs_review" | "approved" | "failed"
    stats: dict                    # tokens, latency_s, retries, fields_verified,
                                   # fields_abstained, cost_chf_estimate
```

## Controlled vocabularies (v1)

| Vocabulary | Values |
|---|---|
| `AffairType` | `motion`, `postulate`, `interpellation`, `written_question`, `initiative`, `petition`, `other` |
| `ActorRole` | `submitter`, `co_signatory`, `addressee`, `respondent`, `rapporteur` |
| `Level` | `federal`, `cantonal`, `municipal` |
| `Language` | `de`, `fr`, `it`, `en`, `other` |
| `EventType` | `submitted`, `registered`, `answered`, `debated`, `decided`, `withdrawn`, `referred`, `closed` |
| `DecisionOutcome` | `adopted`, `rejected`, `partially_adopted`, `withdrawn`, `pending`, `other` |

Vocabularies are versioned with the schema; unknown source terms map to `other` and keep the raw term in the provenance quote.

## Consistency rules (enforced by the validator, SK-E3)

- `provenance` is mandatory for every non-null `extracted` value; forbidden for `inferred` without a note.
- `decision_date` requires `decision ≠ pending`; `decided` event date == `decision_date`.
- `procedural_history` dates are non-decreasing in document order.
- `quote` at `span` on `page` must reproduce `value` under the verifier's normalisation.
- `affair_type`, roles, events, outcomes ∈ vocabularies.
- `language` ∈ vocab; per-field mixed-language quotes are allowed (source fidelity).

## Standards mapping

| Skony | Akoma Ntoso | Popolo | eCH (Politische Geschäfte, in dev.) | Docling |
|---|---|---|---|---|
| `ParliamentaryAffair` | `doc` + `meta` references | — | Geschäft | document |
| `Actor` | `person`/`organization` ref | `Person`/`Organization` | Akteur | — |
| `ProceduralEvent` | `event` | `Event` (ext.) | Geschäftsschritt | — |
| `question_text`/`answer_text` | `block` containers | — | Frage / Antwort | section text |
| `ContentBlock` | `table`/`container` | — | Anhang | table/picture |
| `Provenance` | `FRBR` manifestation ref | — | (to be aligned with Fachgruppe) | page/offset |

The mapping is documented and partial by design — feeding the Fachgruppe discussion is itself a deliverable (insight over completeness).

## Example (abridged)

```json
{
  "affair_id": "743-2021-0142",
  "schema_version": "skony.schema.v1",
  "body_name": {"value": "Gemeinde Nidau", "origin": "extracted",
    "confidence": 0.99, "status": "auto_verified",
    "provenance": {"document_id": "d-88412", "page": 1,
      "span": [212, 227], "quote": "Gemeinde Nidau"}},
  "affair_type": {"value": "motion", "origin": "extracted", "confidence": 0.97,
    "status": "auto_verified",
    "provenance": {"document_id": "d-88412", "page": 1,
      "span": [45, 82], "quote": "Motion der Fraktion …"}},
  "answer_text": {"value": null, "origin": "extracted", "confidence": 0.0,
    "status": "needs_review", "abstain_reason": "illegible_scan",
    "provenance": null},
  "extraction": {"model_name": "Apertus-v1.5-70B", "prompt_version": "v1.3",
    "document_status": "needs_review",
    "stats": {"tokens": 8120, "latency_s": 21.4, "fields_abstained": 1}}
}
```
