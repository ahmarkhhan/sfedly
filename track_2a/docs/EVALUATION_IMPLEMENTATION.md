# B1–B7 evaluation implementation — 16 October 2026

The evaluation audit was closed in the **plan** on 15 October. This document
records the subsequent software implementation and its evidence boundaries.
It complements [A1–A7 implementation](AUDIT_IMPLEMENTATION.md). The frozen
audited plan and original audit reports have not been rewritten.

## Implemented behavior

| Finding | Working software | Evidence still needed |
|---|---|---|
| B1: corpus feasibility | Byte-verified source intake, explicit human language/role/membership/level records, configurable acquisition thresholds, smaller-study bounds, namespaced affairs, retained failures, connected artifact/affair/translation split groups, immutable cohort identities. Metadata hints cannot close the gate. | Competent intake review, actual suitable pairs and a committed split. |
| B2: relation gold | Typed inventoried endpoints, complete membership cross-products including cross-body decoys, within-affair Q/A and response/decision universes, blind packets, original independent annotations, disagreement/adjudication handling, positive/negative/unknown coverage and separate link P/R/F1. Duplicate links cannot earn multiple matches. Research universes bind to the verified test cohort. | Humans must inventory items and label every claimed candidate universe. |
| B3: existing-data comparison | Pinned metadata snapshots and reproducible JSON-pointer queries, saved answers, PDF contribution records with checked source anchors, existing-text detection and a human information-gain gate. A missing structured key cannot hide the same fact in the API's existing text. | A complete baseline assessment and a useful reviewed cross-body answer. The retained API samples alone are not a complete API capability audit. |
| B4: non-circular review | Default workflow reports actions/time only. Optional matched independent-reviewer comparison rejects overlapping gold authors/adjudicators, undisclosed exposure, prior task exposure and missing condition outputs. Gold/plan identities and times are recorded. | Separate actual human sessions against frozen blind gold if an uplift comparison is wanted. |
| B5: competent independent review | Reviewer language/body competence, development calibration, chronological/exposure checks, at least max(25% of test affairs, one per body), all languages, hard cases, roles and claimed relation capability; singly reviewed strata remain visible. Field scorer also reports original reviewer-pair agreement and kappa only where defined. | Actual competent reviewers, calibration and original annotations. Recorded names/competence are declarations, not authenticated identities. |
| B6: schema insight | Independent expressivity, harmonization and pipeline recovery axes, cited human judgments, source-backed counterexamples for partial/negative conclusions, generated matrix and recovery counts. Pipeline failures leave schema conclusions untested. | Checked source examples and substantive human schema/mapping findings. |
| B7: fair experiments | Simple B0, production v0.2 B1, exact saved B1 bytes for B2; identical source windows; separate development-calibrated capacities; every chunk/failure retained; explicit call budgets; raw outputs, actual usage, completion/truncation status and latency; immutable cache and zero-network replay; shared field projection, provenance/contract telemetry, filter tradeoffs and full-cohort slices. | Adequate recorded development completions, frozen real runs and independent human gold. |

These are local research tools. The existing `/scoped` screen still reviews
core fields; typed structural review in that screen was not added. Relation
annotation is available through independent file packets and the local
evaluation service. Statistical scores measure the declared field/link
agreement; they do not establish semantic correctness or nationwide accuracy.

## Run locally

Use Python and the dependencies in `requirements.txt`, from `track_2a/`.
All commands require a **new output path**. Prior evidence is preserved.

```powershell
python scripts/evaluate_study.py schemas --out output/study-input-schemas.json
python scripts/evaluate_study.py inspect --fetch-dir data/private/gold --out output/intake-new.json
python scripts/prepare_evaluation.py --intake output/intake-new.json --metadata data/private/nidau_metadata_sample.ndjson --metadata data/private/docs_6082.ndjson --out output/preflight-new
python -m unittest discover -s tests
```

`prepare_evaluation.py` reads model/endpoint identity from the existing environment
or `.env`, without making a call. On a machine without that configuration, supply
`--model MODEL --endpoint https://HOST/v1`. No credential is written into artifacts.
The metadata arguments select **retained full API response samples**, including
their source text, rather than a reduced candidate-manifest projection.

Preflight retains every source row and original failure, a source-text closure,
an unfilled intake review packet, a candidate cohort, the existing-data baseline,
an explicitly untested feasibility matrix, review/readiness reports and a bounded
DE/FR-hint **development** capacity probe. No reviewer or gold value is fabricated.
Candidate acquisition is distinct from committing an evaluation experiment.

Each new preflight also writes `corpus-coverage.json` and `corpus-coverage.md`.
These show body, language, level, document-role, split, source-status and joint
strata counts from the frozen cohort. Human-checked values are separated from
unverified metadata hints; suspected-scan flags remain explicitly unverified.
The optional structural census adds counts of textless pages, embedded images,
annex markers and table hints, joined to the frozen PDF hashes. These are
inventory detections, not semantic annotations. The artifact is a corpus
coverage report, not an accuracy score. It can also be rebuilt directly from a
saved cohort:

```powershell
python scripts/evaluate_study.py coverage --input output/candidate-cohort.json --out output/coverage.json
```

Add `--structure-census output/structure-census/census.json` to include the
structural inventory.
The command accepts either a cohort JSON or the standard `{"cohort": ...}`
request and writes a matching Markdown view beside the JSON.

## Human intake and gold

In `intake-review-packet.json`, each unit has a `review` slot. A real intake
review records reviewer identity/kind, timestamp, exact artifact/body/affair,
language, scoped role, jurisdiction level, checked pages and a source-based note.
Corrections to unit metadata must match that review. Unknown languages, roles or
unavailable sources remain explicit. Select the actual bounded study before
freezing its cohort; do not retroactively remove inconvenient test failures.

Create a `cohort` request with `units`, `policy`, `links` and `frozen_at`. Units
declare `development` or `test`. Shared artifacts/affairs and confirmed
translation/duplicate links cannot cross those splits. `bounded` policies make
narrower declared studies possible; `small` and `large` enforce the audited
study's minimum thresholds. Passing tests does not close acquisition.

```powershell
python scripts/evaluate_study.py cohort --input completed-cohort-request.json --out output/cohort-frozen.json
python scripts/evaluate_study.py field-packet --input field-packet-request.json --reviewer reviewer-A --out output/blind-fields-A.json
```

The field-packet request contains `cohort` and immutable `texts`. It includes
source material and empty annotation slots, never model suggestions. Use the
published v0.2 field gold contract and original annotation provenance; export
with `scripts/audit_contracts.py export-gold`. Its legacy v0.1 export is a review
artifact and does not establish independent blind gold. For the full protocol,
submit the `review-protocol` schema's reviewer and session records.

## Relationship annotation

Create `relation-universe` input with `nodes`, pinned `texts`, `kinds`,
`frozen_at`, `inventory_note` and the frozen `cohort`. Document/item/decision nodes
need source evidence. Official-number lookalikes in different bodies are
different affairs. Review the full inventory before freezing; relations omitted
from the model's proposals are still candidates.

```powershell
python scripts/evaluate_study.py relation-universe --input relation-inventory.json --out output/relations-frozen.json
python scripts/evaluate_study.py relation-packet --input output/relations-frozen.json --reviewer reviewer-A --out output/relations-A.json
python scripts/evaluate_study.py relation-packet --input output/relations-frozen.json --reviewer reviewer-B --out output/relations-B.json
python scripts/evaluate_study.py relation-merge --input completed-independent-packets.json --out output/relation-gold.json
python scripts/evaluate_study.py relation-score --input relation-scoring-request.json --out output/relation-results.json
```

Annotators independently fill each task's `annotation`, including both checked
endpoint IDs, positive/negative/unknown label, source evidence and rationale.
Merge input has `universe`, complete `packets` and optional `adjudications` keyed
by candidate ID (`label` plus separately recorded `adjudication`). Disagreements
remain unresolved until adjudicated. Gold scoring input has `universe`, the
merged `labels`, and `predictions`. Single, assisted, automated or unknown labels
do not establish relation accuracy. Missing labels remain in coverage accounting.
Image-only passages need an explicitly recorded pinned transcription layer for
these evaluation packets; they cannot claim invented text offsets.

## Freeze and replay the experiment

`experiment-calibrate` input has model/endpoint identity, positive `caps.B0` and
`caps.B1`, and source-only `ExperimentInput` records. Each input retains its text,
chunk manifest and one run per selected chunk. Failed fetches have their frozen
`input_failure` instead of invented source text. Calibration examples must be
development units, never held-out test units. Both contracts must complete below
their declared capacities with reported token usage before the plan can freeze.

```powershell
python scripts/evaluate_study.py experiment-calibrate --input capacity-input.json --out output/capacity-recording.json --mode live --maximum-calls 4 --cache output/study-cache
python scripts/evaluate_study.py experiment-freeze --input experiment-freeze-request.json --out output/experiment-plan.json
python scripts/evaluate_study.py experiment-run --input frozen-run-request.json --out output/experiment-live.json --mode live --maximum-calls 32 --cache output/study-cache
python scripts/evaluate_study.py experiment-run --input frozen-run-request.json --out output/experiment-replay.json --cache output/study-cache
python scripts/evaluate_study.py experiment-score --input experiment-scoring-request.json --out output/experiment-results.json
```

Live execution uses the existing configured Apertus endpoint and transmits the
identified source windows. It needs the applicable authorization. Replay loads
no credential and never falls back to a call on a miss or corrupt cache. Explicit
budgets bound attempts; transport failures and ambiguous remote outcomes persist.
Frozen run input contains `plan`, `cohort`, `inputs`; scoring input contains
`run`, `gold`, `cohort`. `engineering_only` allows clearly labelled synthetic
fixtures and cannot satisfy real-research readiness. Replaying synthetic
completions preserves their original provenance.

For multi-chunk long text, preserve ordered wording including repetitions.
Unresolved alternative scalar values abstain. B0/B1 use the same source windows,
but their prompt/contracts differ: this compares systems, not one causal factor.
Scores report macro counts, source-component counts and body/language/level/role/
hard-case slices with full operational denominators. No independent-sample
confidence is inferred from correlated field slots. Token usage remains unknown
when the provider does not report it; reported totals are explicitly partial.

## Insight and final readiness

The `metadata-baseline`, `novelty`, `feasibility`, `review-protocol`, optional
`review-uplift`, and `readiness` operations share the generated strict request
schemas. Novelty and feasibility requests accept the exact frozen `cohort` so
unrelated corpus findings cannot close its gates. The matrix also exports
Markdown next to its JSON. An untested cell is a valid visible limitation.

The existing local HTTP server exposes the same **offline-only** operations at
`POST /api/v2/evaluation/{operation}` and schemas at
`GET /api/v2/evaluation/schemas`, with its existing origin, token and size guards.
HTTP provides no live experiment operation. CLI output files are immutable
evidence inputs; the HTTP operations validate/return artifacts without persisting
them to the user's review database.

## Validation and remaining evidence

Regression tests exercise false acquisition closure, connected split leakage,
cross-body decoys, negative/unknown denominators, independent packet merge,
calibration/exposure/competence failures, circular uplift, metadata-only novelty,
counterexamples, truncation, budgets, corrupt cache, source-byte replay,
multi-chunk wording, failed-source accounting and HTTP boundaries.

The final full suite passed **197 Python tests** (19.804 seconds), and the
existing scoped-interface suite passed **4 tests**. The initial unmodified suite
passed 133 tests. The 64 additional Python regressions cover the new evaluation
behavior and failure cases. Tests use simulated responses and do not contact a
model endpoint.

The real-source preflight can be reconstructed and checked through the CLI:

```powershell
python scripts/check_evaluation.py --preflight output/evaluation-audit-20261016/final-preflight --intake output/evaluation-audit-20261016/corpus-intake.json --tests-log output/evaluation-audit-20261016/tests.log --out output/evaluation-audit-20261016/replay-verification-new
node --test tests/scoped-ui.test.cjs
```

Local outputs live under `output/evaluation-audit-20261016/`. They include the
baseline and final test logs, real-corpus intake, preflight and a prepared live
capacity probe. The four-call live probe was rejected by automatic approval
review because it would send locally stored PDF text to the external configured
endpoint without explicit payload/destination approval. **No new live call was
made.** Human gold, independent review and real measured study results remain
open evidence gates. The tooling does not turn the prior replay proof or these
engineering tests into an accuracy benchmark.
