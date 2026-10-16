# A1–A7 implementation record — 16 October 2026

Subsequent B1–B7 evaluation software is recorded in
[Evaluation implementation](EVALUATION_IMPLEMENTATION.md), including independent
relation review packets/scoring and the frozen experiment tools. The A1–A7
scope, test count and limits below describe this earlier implementation record.

This records the seven software contracts raised in the independent architecture
audit. It does not declare the broader prototype plan complete. The audit's
planning closure is distinct from the implementation evidence below.

The implementation adds a v0.2 contract, scoped review and comparison layer to
the existing workbench. The main upload/extract workflow still uses v0.1. The
new `/scoped` screen uses the versioned service; importing a recorded v0.2
completion makes no model call. The explicit Python `extract_chunk` function
makes one caller-budgeted request when invoked, with no retry or repair call.
No new live extraction or human gold annotation was performed for this work.

## Implemented contracts

| Finding | Implementation and verification boundary |
|---|---|
| A1: candidate and compatibility | Strict `skony.candidate.v0.2` and `skony.run.v0.2` envelopes require eight field slots per explicit artifact/scope target. Each slot proposes ordered source segments or abstains with a reason. The application resolves offsets and identities. Typed actors, question/response items, events and relations are proposals, with reference and endpoint validation; `null` means not extracted. Benchmark projection requires a target and explicit resolution of alternatives. Legacy projection rejects information loss, including multi-segment or structural output. Three labelled synthetic examples cover a multi-page response, two submitters and minutes containing two affairs. |
| A2: review dependencies | Core-field review pins subject, predicate, assertion/evidence, text snapshot, association/role versions, reviewed scope, mapping versions and conflicts. Current eligibility changes when dependencies change; original decisions remain historical. Membership reassignment needs a successor claim; role/text changes require renewed review; affair-wide scope expansion invalidates aggregate absence; distinct conflicting dispositions block acceptance until explicitly resolved. Identical reruns preserve current eligibility. |
| A3: completeness | Page selection/processing, provider completion and semantic completeness are separate records. Missing chunks, invalid/truncated output and observed unsatisfied continuations remain incomplete; missing provider signals remain unknown. An observed unsatisfied continuation remains incomplete even without chunk history or after a human complete request; chunk outcomes without a manifest are rejected. Successful chunk processing alone leaves semantic completeness unknown. A completeness decision must match the exact claim/scope and check boundaries and required clauses. A fully located, deliberately shortened synthetic answer remains unknown. |
| A4: historical replay | Frozen snapshots contain an immutable, digest-checked closure of review decisions, claims, scope/affair versions, source metadata, text, artifact identities and mappings, with projection/query/serialization versions. Canonical JSON and ordered rows/dependencies determine identities. Mapping changes and affair splits cannot rewrite old results. Superseded/withdrawn status and current-eligibility warnings live outside the deterministic artifact. Historical queries remain available; `current=true` rejects historical snapshots. PDF bytes must be retained separately for original-page display. |
| A5: legacy migration | Additive migration verifies referenced PDFs and takes a consistent SQLite backup including committed WAL state before schema changes. It preserves exact stored page text without reparsing, marks parser/configuration provenance unknown, retains legacy reviews and free-text notes, and marks structured absence scope unverified. Retained manifest source records are reconciled; missing historical associations cannot be reconstructed. Legacy decisions do not become accepted v0.2 exports automatically. |
| A6: gold and scoring | Gold distinguishes `single_annotator_final`, `independently_agreed`, `adjudicated` and `unresolved`, with annotation provenance and checked scope. The primary score accepts eligible known-present/known-absent blind human labels in the first three statuses; independent sensitivity excludes single-annotator labels. Assisted, automated, synthetic and unresolved labels are excluded and counted. Artifact-plus-scope units, frozen cohort outcomes and denominators remain visible; failed inputs earn no correct absence. Matching preserves words, punctuation and case, normalizing whitespace only. These are field-agreement metrics, not semantic accuracy measurements. |
| A7: citations | Exact offsets highlight the immutable text layer; recorded image regions use their recorded render dimensions/transform; evidence without a region opens the page with a labelled transcription/note fallback. Unicode code-point and browser UTF-16 offsets are supplied separately. No PDF coordinates are inferred from text offsets. The isolated synthetic browser fixture demonstrates all three capabilities and a historical-snapshot warning. |

Human review/export of structural or relation proposals and relation accuracy are
unsupported/untested. The converter may retain an unreviewed `related_affair`
proposal with typed endpoints and a printed label; this is not a verified link.
Scoped comparisons return reviewed raw fields and explicit mapping-compatibility
caveats. They do not establish procedural equivalence across bodies.

## Local evidence

The migration report (local evidence, excluded from the public repository)
records unchanged counts and digests for **45 documents, 12 reviews, 14 audit
rows and 7 runs**. It created 45 legacy text snapshots and reconciled 44 retained
manifest source records. The report records the backup directory under
`output/workbench/backups/`; it does not claim to recover lost provenance.

The full suite passed **132 tests on 16 October 2026** (17.267 seconds, exit 0).
The test log (local evidence, excluded from the public repository) and current
verification outputs are retained locally under
`output/audit-implementation-20261015/`; ignored output is not a public packaged
artifact. Tests cover strict
wire validation, evidence boundaries, dependency changes, completeness,
migration rollback/WAL preservation, scoring denominators, immutable replay,
HTTP input boundaries and citation capabilities. Fixtures and browser review
decisions are synthetic engineering QA, explicitly labelled as not gold.

The local verification proof (local evidence, excluded from the public repository)
records the final checks. Browser captures show
text highlighting (local evidence, excluded from the public repository),
a recorded PDF region (local evidence, excluded from the public repository)
and the page/transcription fallback (local evidence, excluded from the public repository).
The synthetic browser checks also confirmed that creating a successor snapshot
clears the old comparison, and changing the selected snapshot clears the result
and disables its download until a new comparison is run.

Offline replay of the exported synthetic snapshot and comparison specification
matched the original comparison ID:
`c062bb263871af0ceb0fee9d827a5e33a6b051b2169a9d8ec41dcfc52d18e8bf`.
This verifies deterministic reconstruction, not extraction quality.

## Commands and service entry points

Run these from `track_2a/` using the project's Python environment:

```powershell
python scripts/audit_contracts.py schemas
python scripts/build_audit_fixtures.py --examples data/sample/contracts-v0.2
python scripts/build_audit_fixtures.py --ui-store output/scoped-qa-new
python scripts/audit_contracts.py compare --snapshot output/scoped-qa-new/snapshot.json --spec output/scoped-qa-new/comparison-spec.json --out output/scoped-qa-new/comparison.json
python -m unittest discover -s tests
```

`--ui-store` requires a new isolated directory. The fixture builder creates
synthetic review decisions for UI verification, not human annotations.

```powershell
python scripts/audit_contracts.py migrate --store output/workbench --source-manifest data/private/gold/fetch_manifest.json --report output/migration-new.json
python scripts/audit_contracts.py score --gold annotations.json --predictions predictions.json --cohort frozen-unit-ids.json --out output/score.json
python scripts/audit_contracts.py export-gold --annotations annotations.json --out output/gold-new
```

Supply the actual retained manifest path for migration; the command above is an
example. Gold/prediction inputs are JSON arrays of their v0.2 objects; the cohort
is a frozen array of `artifact_id:scope_id` strings. Gold export requires a new
or empty output directory and rejects synthetic/automated annotation provenance.
Schema output goes to `docs/contracts-v0.2/`; examples live in
`data/sample/contracts-v0.2/`.

Start the existing server as documented in [Development](DEVELOPMENT.md), then
open `/scoped`. The versioned API uses the existing local origin and write-token
protections (`X-Skony-Token`); requests must match the published strict schemas.

| Route under `/api/v2` | Purpose |
|---|---|
| `GET /schemas` | Candidate, run, review and gold schemas, field dictionary and scope limits. |
| `GET /scopes`, `/affairs`, `/reviews` | Current scoped metadata and review eligibility. |
| `GET /scopes/{id}/claims` | Claims and evidence-capability citations. |
| `POST /sources`, `/affairs`, `/scopes`, `/mappings`, `/text-snapshots` | Register source provenance and versioned scope dependencies. |
| `POST /extractions` | Verify/persist a recorded completion, including invalid raw output; no live call. |
| `POST /claims`, `/corrections`, `/reviews` | Create core-field claims/corrections and dependency-bound review decisions. |
| `GET /eligibility/{decision_id}` | Current export eligibility and invalidation reasons. |
| `POST /snapshots`; `GET /snapshots/{id}` | Freeze a currently eligible closure; retrieve historical closure and warnings. |
| `POST /snapshots/{id}/status` | Append superseded/withdrawn status with a reason. |
| `POST /comparisons`, `/evaluations` | Query a frozen snapshot; score supplied gold/predictions. |
| `GET /artifacts/{sha256}/pdf` | Serve verified pinned PDF bytes for citations. |

## Outstanding validation

Actual human gold, competent semantic review, real-corpus extraction accuracy,
structural/relation accuracy, real multilingual long-answer/OCR evaluation and
analyst usability evidence remain pending. No new OCR pipeline was added.
Docker build/run/rebuild verification still needs a Docker-enabled host. These
limits remain separate from the implemented A1–A7 contracts and synthetic checks.
