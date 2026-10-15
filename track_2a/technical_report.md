# Skony — online Track 2A technical report draft

Design authority: [project direction](../docs/16-project-direction.md).
Completion evidence: [delivery backlog](../docs/18-delivery-backlog.md).
Sources and access limits: [source register](../docs/17-source-register.md).
Shared affair records and evaluation remain planned. Response caching, batch
checkpoints, saved-result import and gold-export safeguards are implemented.
Docker packaging and a synthetic practice replay exist; actual container
execution is still unverified. [Pipeline evidence](docs/PIPELINE_VERIFICATION.md).

Status: extraction and local review implementation, 15 October 2026. This Markdown file is not yet
the required final PDF. One real-document pilot is complete; dataset-level
extraction accuracy has not been measured.

## Problem and contribution

Investigate which parliamentary affair fields can share a common representation
across bodies and languages. Preserve original wording, explicitly abstain when
evidence cannot be located, and record where the shared schema cannot represent
the source faithfully.

## Implemented first slice

PDF → page text and digest → Apertus schema-constrained prompt → strict JSON
validation → evidence lookup → review-required JSON. The output has eight
raw fields. Normalisation and controlled vocabularies are planned, rather than
inferred and silently treated as source text.

Each non-null result includes a document ID, page number, original quote and
character offsets into the unchanged extracted page text. `source_located`
means a string was found; it does not establish correct field assignment or
faithfulness of question/answer boundaries. All such results require review.

## Validation so far

82 engineering tests passed on local Python 3.11. The client was exercised with
mocked HTTP transports and the real CSCS service. Tests cover fabricated
quotes/values, wrong page attribution, repeated quotes, missing evidence,
textless/oversize input, malformed schemas, truncated/mismatched endpoint
responses, line-break span recovery and obviously corrupt submitter OCR. Review
tests also cover persistence, stale revisions, fabricated correction rejection,
explicit absence, visual transcription, audit snapshots, model reruns preserving
human decisions, reviewed-only export and local route/secret isolation.

New execution checks cover replay blocking live calls, synthetic-fixture hashes,
restart persistence and mapped localhost Host/Origin checks. A clean public-source
copy starts without private data/keys and serves the PDF/image and reviewed export.
The bundled practice data are authored examples, not model output or evaluation gold.

The batch/cache checks cover full effective-request identity, corrupt-cache
rejection, schema-invalid response replay, actual call accounting, preserved
failed downloads, unchanged manifests, interrupted resume and idempotent
workbench import. Gold-export checks exclude synthetic/QA records and prevent
stale labels from a previous export directory entering a new manifest.

An approved real-data engineering proof processed one DE Nidau PDF and one FR
Genève PDF using Apertus 1.5 70B at CSCS. The first run made two calls, reporting
3,953 total tokens and 13.594/9.406 seconds. Offline replay, with no credential
and an HTTP-rejecting transport, used two cached responses and produced identical
verified results with zero model calls. One failed-fetch row remained in both
ledgers. This demonstrates pipeline reuse, not semantic accuracy or multilingual
benchmark coverage. Both results were imported without altering existing review
decisions. The store has 12 decisions across four documents, one mechanically
complete; it is not yet a frozen, competence-checked evaluation gold set.

On one scanned Nidau postulate with an existing OCR layer, the 8B pilot first
copied the schema and then returned inconsistent null/evidence combinations.
Both were rejected. The 70B pilot returned valid fields. Replaying that recorded
response with verifier `evidence-v0.2` located the title, type, printed date and
request; it abstained on the garbled submitter and absent answer/decision fields.
The 70B call took 7.234 seconds and used 1,725 tokens. These are single-call
observations, not a benchmark or a gold-set result. Full pilot details are in
`../docs/12-cscs-pilot.md`.

## Planned evaluation

Use separate development and held-out human-reviewed documents spanning German
and French and multiple parliamentary bodies. Compare a fair simple baseline,
raw Apertus extraction and extraction with evidence checks. Report field
precision/recall, abstention/coverage, source-location accuracy, question/answer
pairing, latency and actual token usage. Scans and minority layouts must remain
visible in the report rather than being filtered out of the denominator.

## Current limitations

The local workbench displays PDF page images, source text and highlighted spans.
Reviewers can confirm, correct, record absence or undo. Decisions are separate
from model suggestions in SQLite, with before/after audit history. Visual
transcriptions are explicitly labelled and carry no claimed text offsets.
Exports contain reviewed fields only, plus a list of remaining unreviewed fields.
Reviewer identity is a self-entered label; multi-user authentication is not implemented.

No OCR, multi-page field assembly, controlled vocabulary mapping,
cross-body query interface or gold-set evaluation is implemented yet. The Docker
runner is packaged but has not been built/run in this environment. Whitespace-only
matching recovers some layout differences but preserves
wording, punctuation and original offsets. Other OCR/layout differences still
require review; the OCR marker heuristic does not detect all corrupt names.
Copied text can still be assigned to the wrong semantic field. Model identity
must be confirmed against the provider's documented served-model mapping.

## Deployment and licensing

The application uses a configurable Apertus endpoint. A Swiss endpoint and
self-hosted endpoint are deployment targets; air-gapped operation has not been
tested. Code follows Apache-2.0. Documentation is CC-BY-4.0. A source manifest
must state individual third-party data licences before source material is
redistributed or a dataset licence is applied to our own annotations.

