# 08 — UI / UX Design

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

Two surfaces: the **Review Workbench** (trust-building, mirrors OpenParlData's production tool) and the **Query interface** (the payoff). A dashboard ties them together.

## Screen 1 — Dashboard

- Corpus stats: documents, affairs, extraction coverage, auto-verified vs needs-review.
- Trust meters: verification-failure rate, abstain rate (by reason), gold-set F1 (latest eval).
- Cost/latency strip: tokens, CHF/doc, p95 latency.
- Entry points: Review queue · Query · Documents.

Purpose in the demo: show this is an operations tool, not a chat toy.

## Screen 2 — Review queue (SK-C4)

Table of documents needing attention, sorted ascending by lowest-field-confidence.

| Document | Body | Lang | Type | Unverified fields | Reason | Confidence |
|---|---|---|---|---|---|---|
| d-88412 | Nidau | DE | Motion | answer_text | illegible_scan | 0.41 |

Filters: body, language, affair type, reason code. One click opens the compare view.

## Screen 3 — Compare view (SK-C1/C2/C3/C5) — the core screen

```
┌───────────────────────────────┬──────────────────────────────────┐
│  PDF page (or page image)     │  Extracted fields                 │
│  ┌─────────────────────────┐  │  ┌──────────────────────────────┐ │
│  │ …Motion der Fraktion…   │◄─┼──│ affair_type: motion     [✓]  │ │
│  │ ▓▓highlighted span▓▓    │  │  │ submitters: M. Muster   [✓]  │ │
│  │                         │  │  │ question_text: "…"      [✓]  │ │
│  │                         │  │  │ answer_text: ∅ ⚠ illegible   │ │
│  │                         │  │  │   [suggest][edit][reject]    │ │
│  └─────────────────────────┘  │  └──────────────────────────────┘ │
│  [PDF] [Text] [Docling] [JSON]│  Origin: ● extracted ◐ inferred ✎ manual │
└───────────────────────────────┴──────────────────────────────────┘
```

Interactions:
- **Click a field** → source view scrolls & highlights the provenance span; click a span → field flashes (SK-C2).
- **Field states** encoded by colour + icon + origin tag (extracted/inferred/manual); unverified fields can never look verified.
- **Correct inline**: editing keeps the provenance box editable, marks origin `manual`, writes to the audit log (SK-C3).
- **Approve document** button enabled when all fields resolved; keyboard-first flow (accept = `a`, edit = `e`, next = `→`) so a reviewer clears the queue fast — that speed *is* the demo.

## Screen 4 — Query (SK-D1/D2/D3)

- Left: structured filters (type, body, party, date range, outcome, keyword) → live result table.
- Top: natural-language box → cited answer. Every sentence ends with a citation chip `[1]`; clicking it jumps to the compare view at the exact span.
- Empty-corpus questions produce an explicit refusal ("not in the extracted corpus") — shown proudly; abstention is the brand.

## Demo choreography (4-minute finals slot)

1. Dashboard → "300k documents sit like this" (problem in one image).
2. Live extraction of one fresh document — watch quotes resolve to spans in real time.
3. Compare view: accept two fields, watch one abstain on a scanned page — *"it says so, it doesn't guess."*
4. Killer query answered with citations; click a citation → lands on the highlighted source. **This is the voting moment.**
5. Fallback: screen recording of the same flow, pre-rendered (venue Wi-Fi rule).

## Accessibility & i18n

- UI chrome in DE + FR (Bern is bilingual; most teams demo English-only).
- Extracted content always in source language; translations labelled `generated`.
- Colour is never the only state signal (icons + text); keyboard navigable; WCAG-AA contrast.

## Non-goals for the hackathon UI

No accounts/permissions, no theming, no mobile layout. Time saved goes into verifier quality and eval numbers — the UI only has to make trust visible.
