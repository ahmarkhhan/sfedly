# Independent architecture audit — GPT-6-astra

**Date:** 15 October 2026, Asia/Karachi.
**Auditor:** GPT-6-astra, high reasoning, isolated initial context.
**Reviewed document:** docs/19-prototype-excellence-plan.md, revision 1.0.
**Verified SHA-256:** e10ea79787520d8a405587fe745fe37e43567114ae7ffa62635809073698f09b.
**Scope:** read-only planning audit explicitly requested by the user.
**Original verdict:** conditional.

## Auditor's original report

The plan is a strong basis for implementation, with appropriate ambition and conservative research claims. Before implementation, clarify the contracts below. These are planning findings, not measured defects, a judge score, or certification.

Read-only evidence included the archived official brief and current schema.py, pipeline.py, pdf.py, cache.py, verify.py, and relevant portions of review.py and corpus.py. No application tests, extraction runs, model calls, secret inspection, or edits were performed.

### A1 — High: The richer representation lacks a concrete extraction and compatibility contract

**Sections:** §5 “Entities and identity” and “The shared core”; §9 “Gold schema”; §10 “Scoring units”; §11 implementation map.

The current CandidateExtraction consists of eight scalar fields, each with one page and quote. The plan introduces actor arrays, multiple events, question/response items, scoped affairs and multi-segment evidence, but does not define which of these the converter proposes, which humans author, or how they project into the eight benchmark fields. A generic assertion list alone does not establish cardinality, subject ownership, relation endpoints or required field slots. Implementers could produce mutually incompatible exports and denominators while apparently following the plan.

**Minimum correction:** Specify one versioned candidate/output envelope, a field dictionary with subject and cardinality, typed relation endpoints, and explicit legacy projection rules. Include examples for a multi-page response, two submitters, and minutes containing two affairs. Define what cannot be represented in v0.1 and reject or label lossy export. State whether related-affair links from the brief are supported or untested. Freeze the corresponding scoring units before W4.

### A2 — High: Review validity is bound too narrowly to source snapshots

**Sections:** §5 field states and ReviewDecision; §7 “Review actions and gold mode”; §12 T5.

Preserving a decision when its text snapshot is unchanged is necessary but insufficient. The same unchanged quotation can be reassigned to another affair, acquire a different document role, or become part of a conflict. A previously valid “no response in reviewed material” assessment cannot automatically apply after another response document is linked. The plan mentions scoped decisions but does not define these dependency and eligibility rules.

**Minimum correction:** Bind reviewed claims to a subject, predicate, evidence, scoped association version and reviewed-scope identity. Define a small invalidation table: text changes invalidate relevant span approvals; membership/role changes invalidate dependent semantic approvals; expanded scope requires a new aggregate absence/completeness decision; new conflicting assertions block affected current exports pending resolution. Preserve the original decision as valid historical evidence for its original scope. Add a fixture for each dependency change.

### A3 — High: Chunk completeness is being used to support a stronger content-completeness promise

**Sections:** §6 “Long-document processing”; §12 T2 and T7.

Processing every selected page does not establish that the extracted response contains every required clause. A model can return valid JSON containing only the first paragraph while all chunk jobs succeed. Likewise, a skipped continuation is not always detectable from extracted text. The current pipeline receives response text and usage without a richer completion-status contract. “Missing middle/end pages trigger incomplete state” therefore needs an explicit, implementable basis.

**Minimum correction:** Separate input coverage, generation completion, and semantic section completeness. Record selected versus available pages, chunk outcomes, provider finish reason when available, boundary/continuation evidence, and a completeness state of complete/incomplete/unknown. Require a checked section boundary or human completeness decision before a long response is represented as complete. Retain unknown when omission cannot be mechanically detected. Include a valid, fully located but deliberately shortened response in acceptance fixtures.

### A4 — Medium: Snapshot invalidation conflicts with immutable historical replay unless its meaning is narrowed

**Sections:** §4 immutable artifacts; §5 ReviewedSnapshot; §7 changed mappings; §8 deterministic query; §12 Q4/P1.

§7 says a mapping change invalidates the dependent comparison snapshot, while other sections require immutable snapshots and identical historical replay. It is unclear whether “invalidate” means mutate, prevent historical access, or mark unsuitable for current use. A snapshot that merely points to mutable mapping/relationship records cannot reproduce its old result.

**Minimum correction:** Define frozen snapshots as immutable dependency closures containing or pinning decisions, association versions, scope, mappings, query/serialization version and cited artifacts. Later corrections create a successor and a separate superseded/withdrawn status; historical replay remains available with its historical warning. Specify canonical ordering and digest inputs. Test an old comparison after changing a mapping and after splitting an affair.

### A5 — Medium: The migration needs an explicit policy for historically missing provenance

**Sections:** §2 existing evidence; §11 “Storage and migration details”; §12 T3/P3.

Existing document_json preserves page text, but the current document schema does not record parser identity. Legacy absence reviews contain a free-text note rather than machine-readable checked scope. Existing artifact deduplication and source backfill may already have collapsed multiple source records. Migrating those rows cannot reconstruct facts that were never stored; hashing them does not restore their provenance.

**Minimum correction:** Create legacy text snapshots directly from stored page text, with parser/configuration origin explicitly unknown unless independently recoverable. Do not reparse and reuse old offsets. Preserve free-text absence notes while marking structured scope unverified until checked. Reconcile historical source manifests where available, documenting irrecoverable association gaps. Define a consistent SQLite backup including WAL state and verify referenced artifact files before migration. Preserve recoverable history without promising reconstruction of lost history.

### A6 — Medium: The gold eligibility rule is inconsistent with the staffing protocol

**Sections:** §9 “Gold schema and review protocol”; §10 field metrics.

The strict scoring subset requires “adjudicated known-present or known-absent labels,” but independent annotation covers only at least 25% of held-out affairs, with the remainder singly annotated. Under a literal reading, most planned gold is ineligible; under a loose reading, “adjudicated” may conceal single-review labels. The result changes accuracy denominators materially.

**Minimum correction:** Define distinct statuses for single-annotator final, independently agreed, adjudicated, and unresolved. State explicitly which enter the primary score and report counts by status; optionally report a sensitivity result on the independently checked subset. Do not imply that singly annotated labels received independent adjudication.

### A7 — Medium: The citation interaction promises highlighting where the evidence model permits no highlight coordinates

**Sections:** §1 flagship workflow; §5 provenance; §8 “Result behavior”; §12 U2.

Evidence coordinates are optional, human image evidence may have only a page and note, and the retained native parser yields page text without a guaranteed text-to-image coordinate map. Yet the comparison promises every citation will highlight its supported segment. An implementation could satisfy the evidence schema while failing the advertised interaction or fabricating an approximate PDF highlight.

**Minimum correction:** Define citation behavior by evidence capability: exact text-layer highlight for offset evidence, PDF-region highlight when a recorded transform and region exist, and a clearly labelled page-plus-transcription/note fallback for image-only evidence. Require richer anchors only for claims specifically demonstrated as PDF-region highlighting. Add one acceptance example per capability.

### Strengths

- The plan correctly centers affairs and distinguishes source identities, PDF bytes, scoped document roles and independent links.
- It treats quotation location, semantic support, human review and procedural equivalence as separate claims.
- Native/OCR separation, immutable page text, explicit Unicode offsets and honest image transcription address important provenance hazards.
- The existing modular application is reused sensibly; the proposed workload does not call for a distributed architecture.
- The comparison, feasibility matrix and partial/negative findings align well with the archived brief's emphasis on insight and applicability.
- Baseline reuse, frozen cohorts, failure accounting, human staffing and the separation of internal score targets from official criteria are unusually well specified.

### Remaining implementation-only validation

The amended plan would still need demonstrated migration preservation; working scoped review and invalidation behavior; actual DE/FR multi-page and OCR cases; interruption/restart accounting; observed scorer outputs on known-answer fixtures; deterministic offline reconstruction; and analyst usability evidence. Neither this audit nor another LLM audit can substitute for those checks or establish semantic extraction accuracy.

## Plan author's disposition

All seven findings were accepted and addressed in revision 1.1. The specific changes are mapped in [the plan's audit ledger](../19-prototype-excellence-plan.md#16-independent-llm-audits-and-incorporated-corrections). The independently authored original report above is distinct from this disposition. A closure check against the frozen revised document is recorded below when returned by the auditor.

## Auditor's closure check

**Reviewed revision:** 1.1.
**Verified SHA-256:** 32249cd419b72ec6dd181ff2a4e046c5b2baa7c587ac859996244b69b19aa86e.
**Revised verdict:** ready as an implementation plan.

All seven findings are closed at the planning level, based on the substantive sections and acceptance gates.

| Finding | Status | Closure evidence |
|---|---|---|
| A1 — Extraction/projection contract | Closed | §5 specifies strict wire keys, eight required slots, proposal/abstention rules, subject cardinalities, typed endpoints, reference validation and benchmark projections. Three concrete examples explain multi-page, multi-actor and multi-affair behavior; lossy compatibility exports are refused. |
| A2 — Review dependencies | Closed | §7 binds decisions to semantic and scope dependencies. Its change table covers membership, role, expanded scope and new conflicts; T5 requires corresponding fixtures. Historical decisions remain preserved. |
| A3 — Completeness | Closed | §6 separates input coverage, generation completion and semantic completeness. Unknown is retained where omissions cannot be detected; T2 explicitly covers a located but shortened answer. |
| A4 — Immutable historical replay | Closed | §7 defines a frozen dependency closure, canonical digests, successor snapshots and separate status warnings. Q4 requires historical reproduction after mapping, role or affair changes. |
| A5 — Legacy migration provenance | Closed | §11 requires a consistent SQLite/WAL backup and artifact manifest, preserves exact legacy text, records unknown parser provenance, and prevents unverified legacy scope from entering new accepted exports. |
| A6 — Gold eligibility | Closed | §9 distinguishes single-annotator final, independently agreed, adjudicated and unresolved labels. Primary-score eligibility and an independently checked sensitivity subset are explicit. |
| A7 — Citation capabilities | Closed | §8 and U2 distinguish text highlights, recorded PDF-region highlights, and honest page/transcription fallback without invented coordinates. |

**Remaining material blocker from A1–A7: none.** Formal schemas, migration behavior, dependency enforcement, completeness checks and citation interactions still require implementation and the prescribed verification. This closure establishes plan readiness only; it does not certify implemented quality, extraction accuracy or marks.

The check was read-only. No application changes, tests, extraction runs or external model calls were made.
