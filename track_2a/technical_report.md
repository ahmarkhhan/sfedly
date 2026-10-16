# Skony — Track 2A OpenParlData: Technical Report

Repository: <https://github.com/ahmarkhhan/sfedly> (built from the HackApertus project template).
Build and completion evidence: [BUILD_STATUS](docs/BUILD_STATUS.md).
Scoped affair contracts and offline evaluation tooling are implemented;
a frozen four-document human gold set (DE+FR, three bodies, two levels) exists
with a first in-sample agreement measurement. Response caching, batch
checkpoints, saved-result import and gold-export safeguards are implemented.
Docker packaging and a synthetic practice replay exist; actual container
execution is still unverified. [Pipeline evidence](docs/PIPELINE_VERIFICATION.md).

Status: extraction and local review implementation, 16 October 2026. A
four-document frozen gold set is exported and a first development-set
agreement measured (31/32 field slots); held-out extraction accuracy has not
been measured. Measured run evidence: [RESULTS](docs/RESULTS.md).

## Judging criteria and where they are addressed

| Criterion (official brief wording) | Where it is addressed | State |
|---|---|---|
| Insight: a well-founded conclusion on common-schema feasibility; partial or negative counts | [Honest limits](#honest-limits); [RESULTS](docs/RESULTS.md#honest-limits) | Partial: a common raw-field representation proved feasible for the eight-field slice tested; the unresolved seam is question/answer pairing and role assignment across bodies |
| Breadth: demonstration across document types, languages and levels of government | [RESULTS §Measured runs](docs/RESULTS.md#measured-runs); [RESULTS §Review and gold-set state](docs/RESULTS.md#review-and-gold-set-state) | Narrow but real: gold v1 spans DE + FR, three bodies (municipal Nidau, cantonal Genève, cantonal Waadt) and two levels of government; born-digital plus one scanned/OCR-layer document; a 44-PDF hash-verified corpus awaits review |
| Traceability and faithfulness: no invented values; span-level provenance; flag rather than guess | [Implemented first slice](#implemented-first-slice); `src/skony/verify.py` (abstains on unlocated, fabricated or ambiguous evidence); strict-validation rejection tests in `tests/test_evidence.py` | Implemented: every non-null field carries document ID, page, original quote and character offsets; unverifiable values abstain |
| Built with Apertus | `src/prompts/extract.txt`; [RESULTS](docs/RESULTS.md) (recorded `swiss-ai/Apertus-v1.5-70B` runs with token and latency observations) | Yes, at CSCS; development-time only, not redistributed |
| Reusable outputs: public repository with converter, prompts, validator and README samples | [README](README.md) quick-start; [RESULTS §Reproduce](docs/RESULTS.md#reproduce-public-source-no-credentials-no-docker); hash-checked synthetic fixture in `data/sample/`; current offline engineering suite | Public synthetic replay runs without credentials; the real DE/FR cache replay requires privately retained inputs |
| Judge execution: `make run` in Docker | root and track `Makefile`, `Dockerfile`, `compose.yaml`, `scripts/check_docker.py`, CI workflow `.github/workflows/docker-verify.yml` | Packaged, unverified on the development host (no Docker/WSL there); the clean public-source start passes outside a container |

## Problem and contribution

Investigate which parliamentary affair fields can share a common representation
across bodies and languages. Preserve original wording, explicitly abstain when
evidence cannot be located, and record where the shared schema cannot represent
the source faithfully. Our partial conclusion: a common raw-field
representation is feasible for the eight-field slice tested — fields were
located with original wording and spans across one DE municipal and one FR
cantonal document — while question/answer pairing and role assignment
across bodies remain the unresolved seam.

## Implemented first slice

PDF → page text and digest → Apertus schema-constrained prompt → strict JSON
validation → evidence lookup → review-required JSON. The output has eight
raw fields. A draft controlled-vocabulary layer maps labels to 33 stable term
IDs (229 DE/FR/EN aliases) while preserving raw values and explicit unmapped
outcomes. A structural inventory detects annex markers, images and table
regions with provenance; it does not interpret their values. The research
explorer searches imported PDF text and exports cited briefs. Scoped v0.2
review, comparison, migration, gold eligibility and offline evaluation tooling
are implemented; human gold and measured semantic accuracy remain pending.

Each non-null result includes a document ID, page number, original quote and
character offsets into the unchanged extracted page text. `source_located`
means a string was found; it does not establish correct field assignment or
faithfulness of question/answer boundaries. All such results require review.

## Validation so far

245 engineering tests and 16 interface-controller tests passed on local Python 3.11 / Node 24 ([RESULTS](docs/RESULTS.md)). The client was exercised with
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
decisions.

A frozen gold v1 set was exported on 16 October via `scripts/export_gold.py`:
four documents, all eight fields each carrying an explicit human confirm /
correct / absent decision (32 slots). Coverage: DE municipal Nidau ×1, FR
cantonal Genève ×2, FR cantonal Waadt ×1 — three bodies, two levels. The
export is checksummed (manifest sha256 prefix `27332723140e1ad8`) and excludes
41 unreviewed imported documents by gate. Against the recorded model
suggestions, 31 of 32 slots agree (19 confirmed values, 12 correct absences);
the single correction was a Genève title the reviewer replaced with the full
verbatim text — field agreement 96.9% on this development set. All 12
answer/decision slots were correctly absent (request-role documents). The
annotation files hold verbatim source quotes and stay with the private corpus
until item-level source licences are stated; tooling and manifest format are
public. Evidence: [RESULTS §Review and gold-set state](docs/RESULTS.md#review-and-gold-set-state).

On one scanned Nidau postulate with an existing OCR layer, the 8B pilot first
copied the schema and then returned inconsistent null/evidence combinations.
Both were rejected. The 70B pilot returned valid fields. Replaying that recorded
response with verifier `evidence-v0.2` located the title, type, printed date and
request; it abstained on the garbled submitter and absent answer/decision fields.
The 70B call took 7.234 seconds and used 1,725 tokens. These are single-call
observations, not a benchmark or a gold-set result.

## Planned evaluation

Use separate development and held-out human-reviewed documents spanning German
and French and multiple parliamentary bodies. Compare a fair simple baseline,
raw Apertus extraction and extraction with evidence checks. Report field
precision/recall, abstention/coverage, source-location accuracy, question/answer
pairing, latency and actual token usage. Scans and minority layouts must remain
visible in the report rather than being filtered out of the denominator.

## Honest limits

Each bullet states a limitation, its consequence and where the evidence is.
This section, not the feature list, is the insight contribution.

- **Two documents are not coverage.** The DE/FR batch contains two team-selected
  real PDFs; the earlier scanned Nidau pilot is recorded separately above. Nothing measures accuracy on unseen
  documents; breadth above is corpus breadth, not measured extraction
  breadth. Evidence: [RESULTS](docs/RESULTS.md).
- **In-sample tuning.** The prompt (`raw-v0.2`) and verifier (`evidence-v0.2`)
  were shaped on the same pilot documents that demonstrate them. The replay
  results are self-consistent by construction, not evidence of
  generalisation. Evidence: [PIPELINE_VERIFICATION](docs/PIPELINE_VERIFICATION.md).
- **Small, single-annotator, in-sample gold.** Gold v1 is four documents,
  FR-weighted (3 FR / 1 DE), each single-annotated by a team reviewer with no
  inter-annotator agreement measured. The 96.9% agreement figure is computed
  on the same documents that shaped the prompt and verifier — it is
  self-consistency evidence, not a generalisation rate, and held-out
  precision/recall remain unmeasured. Evidence: [RESULTS §Review and gold-set state](docs/RESULTS.md#review-and-gold-set-state).
- **Located is not correct.** `source_located` proves a string match, not
  semantic assignment: a value can occupy the right span and the wrong field.
  Every located field therefore requires review; question/answer pairing is
  unvalidated. Evidence: [Implemented first slice](#implemented-first-slice).
- **Docker is packaged, not proven.** No container has been built on the
  development host (no Docker/WSL); the CI workflow and `scripts/check_docker.py`
  are ready but unexecuted there. The official judge path could therefore
  fail on first contact; `scripts/check_clean_start.py` covers the
  non-container path. Evidence: [PIPELINE_VERIFICATION](docs/PIPELINE_VERIFICATION.md).
- **One previously flaky test.** `test_mutation_requires_token_and_matching_origin`
  in `tests/test_review.py` failed intermittently on the development host; it
  passed five consecutive runs on 16 October and the fresh-clone suite is
  passing at the time of that earlier check. Named so a judge re-running it is not surprised. Evidence:
  `python -m unittest tests.test_review.ServerTests.test_mutation_requires_token_and_matching_origin`.
- **Heuristic roles and languages.** Corpus role and level tags are heuristic
  hints; 13 of 45 manifest rows are unknown-language. Level-of-government
  breadth claims wait for reviewed metadata. Evidence:
  [BUILD_STATUS](docs/BUILD_STATUS.md).
- **Conservative matching has blind spots.** Whitespace-only recovery cannot
  bridge OCR reflow, and the corrupt-name marker does not catch all
  corruption. Some real values will read as abstentions until review —
  accepted as the price of never guessing. Evidence: `src/skony/verify.py`.

The local workbench displays PDF page images, source text and highlighted spans.
Reviewers can confirm, correct, record absence or undo. Decisions are separate
from model suggestions in SQLite, with before/after audit history. Visual
transcriptions are explicitly labelled and carry no claimed text offsets.
Exports contain reviewed fields only, plus a list of remaining unreviewed fields.
Reviewer identity is a self-entered label; multi-user authentication is not implemented.

OCR and automatic multi-page field assembly remain unimplemented.
Controlled-vocabulary mapping, structural inventory and a source-text research
explorer now exist; their synthetic engineering checks do not establish
cross-body semantic comparability. Gold-set evaluation still requires
independent human annotation. The Docker
runner is packaged but has not been built/run in this environment. Whitespace-only
matching recovers some layout differences but preserves
wording, punctuation and original offsets. Other OCR/layout differences still
require review; the OCR marker heuristic does not detect all corrupt names.
Copied text can still be assigned to the wrong semantic field. Model identity
must be confirmed against the provider's documented served-model mapping.

## Deployment and licensing

The application uses a configurable Apertus endpoint. A Swiss endpoint and
self-hosted endpoint are deployment targets; air-gapped operation has not been
tested.

| Component | Licence | Note |
|---|---|---|
| Application code (this repository) | Apache-2.0 | per event terms |
| Documentation and this report | CC-BY-4.0 | per event terms |
| Bundled synthetic fixture (`data/sample/`) | CDLA-Permissive-2.0 | authored; fictional people and parliament |
| Runtime: pydantic, httpx, pypdf, PyMuPDF (pinned in `requirements.txt`) | MIT / BSD-3-Clause; PyMuPDF AGPL-3.0 or commercial | PyMuPDF licensing must be satisfied when distributing the application; see upstream licence |
| Apertus v1.5 via the CSCS endpoint (development time) | Apache-2.0 (model) | not redistributed |
| OpenParlData source PDFs (private corpus) | source-specific terms | not redistributed; a source manifest must state item-level licences before any redistribution or before a dataset licence is applied to our own annotations |
| Gold v1 annotations (4 documents, contain verbatim source quotes) | our decisions + source-specific quote terms | retained with the private corpus until item-level licences are stated; export tooling and manifest format are public |
| Container base (`python:3.11-slim`, Poppler) | Debian package terms | runner image only |
