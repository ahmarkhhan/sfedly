# Build status — 16 October 2026

Target: Hack Apertus **online**, Track 2A / OpenParlData. Deadline: 16 October,
12:00 CEST = **15:00 Asia/Karachi**. This is a starter, not a complete submission.

Current design authority: [project direction](../../docs/16-project-direction.md).
Implementation priorities and acceptance evidence are in the
[delivery backlog](../../docs/18-delivery-backlog.md); sources are in the
[source register](../../docs/17-source-register.md). These documents distinguish
official requirements from our internal targets and future features.

**Research product update, 16 October:** `/explore` now provides full-text search
over imported PDFs (including unextracted documents), parliament/language/evidence
filters, DE/FR/IT/EN topic keyword hints, source-metadata dossiers, per-document
requests/answers/decisions, a conservative dated-event timeline, raw submitter
blocks, evidence reading and deep links into field review. Research briefs export
all filtered results as JSON or CSV, with source hashes, revisions, citations and
review status. This read-only projection makes no model calls or review decisions.
Metadata associations remain unverified, missing text never implies a pending
affair, and document review is separate from v0.2 scoped acceptance. See the
[explorer guide](EXPLORER.md). The full regression suite passes **245 Python tests
and 16 interface-controller tests**; browser QA used a read-only view of the existing
local corpus. No human gold or additional live extraction was created.

**Earlier A1–A7 record, 16 October:** **132 local engineering tests passed**. The seven
audited software contracts are implemented in a v0.2 layer: explicit candidate/run
envelopes, dependency-bound scoped review, separated completeness states,
immutable offline comparison, additive legacy migration, human gold eligibility
and field scoring, and three citation capabilities. See the
[implementation record](AUDIT_IMPLEMENTATION.md) for commands, routes and limits.
The new `/scoped` screen exposes this layer; the main extraction screen retains
v0.1, and v0.2 HTTP extraction imports recorded output. Structural/relation human
review and relation accuracy remain unsupported/untested. New fixtures and browser
checks are synthetic, with no new human gold or live model call.

**Evaluation tooling update, 16 October:** B1–B7 now have acquisition/split gates,
independent relation packets and scoring, metadata novelty checks, reviewer
protocol checks, a three-axis feasibility matrix and capacity-frozen B0/B1/B2
execution/replay. See [evaluation implementation](EVALUATION_IMPLEMENTATION.md)
for current commands, regression evidence and remaining human/research gates.
The previous 132-test statement above is the historical A1–A7 record; the new
evaluation test log is retained under `output/evaluation-audit-20261016/`.
That evaluation update recorded **197 Python tests and 4 interface tests**. Real-corpus
preflight retains 45 source rows, 44 pinned PDFs and one failed source. Human
gold and independent annotation are still missing. The prepared four-call
development probe needs explicit external-transmission approval; it made no calls.

**Coverage report addition, 16 October:** the frozen-cohort workflow now emits
JSON and Markdown coverage tables by body, language, government level, document
role, source status, split, and joint strata. Human-checked values are separated
from metadata hints. Replaying the saved 45-row real-source cohort reports 44
pinned PDFs, one failed source retained, 24 German hints, 8 French hints, 13
unknown-language hints, and zero human-verified intake units. This is coverage
accounting only; it does not satisfy gold review or extraction evaluation. The
optional structural census joins by PDF hash and adds textless-page, image,
annex-marker and table-hint strata. It records four PDFs with textless pages,
22 with embedded images, five with annex markers and one with table hints; see
[structural census methods and limits](STRUCTURE.md). Intake scan flags are not
a substitute for this PDF-level census.

The earlier corpus/cache/batch/import/export tools were checked and hardened; see the
[verification report](PIPELINE_VERIFICATION.md) and [batch guide](BATCH_EVALUATION.md).
All 44 downloaded PDFs match their pinned hashes; the 45th row is a preserved
failed download. The corpus metadata contains 24 DE, 8 FR and 13 unknown-language
rows, not 45 language-verified sources. Roles are heuristic hints until reviewed.

After explicit approval, one DE and one FR PDF were processed by Apertus 1.5 70B
at CSCS: two live calls, 3,953 reported tokens. A second run used an empty API
credential, returned two identical cached results, made zero calls and preserved
the failed-fetch row. Both results were imported into the main workbench.
Reimport was unchanged and preserved all **12 existing field decisions** across
four documents. One document passes the eight-decision mechanical export gate;
its source language is unknown and reviewer competence/semantic accuracy have
not been certified here. It is not a frozen evaluation gold set. No human
annotation was created by this automation.

Clean public-source startup/preview/review/restart/export also passes. Docker
packaging and an isolated build/run/persistence verifier are implemented, but
Docker and WSL are absent here; actual container execution remains unverified.
The public project is a Git checkout; local private workbench state is excluded. The deterministic field scorer is
implemented; human gold and real-corpus evaluation remain pending.

The main-store migration preserved counts and digests for 45 documents, 12
reviews, 14 audit rows and 7 runs. It retained 45 exact legacy text snapshots and
reconciled 44 retained manifest source records. Legacy parser provenance remains
unknown and structured absence scope unverified. Old decisions remain preserved
and excluded from accepted v0.2 exports until reviewed against the new contracts.
Backup and local evidence paths are recorded in the
[implementation record](AUDIT_IMPLEMENTATION.md).

## Implemented and checked

- Versioned raw extraction schema: eight fields, explicit abstention, strict validation.
- PDF intake: page numbers, original extracted text, file digest, textless-page flags.
- Apertus client configured through the required `LLM_*` variables.
- Prompt requiring source wording and a quote on the claimed page.
- Exact and whitespace-only quote-to-offset resolution into the original page text,
  rejecting fabricated, missing or ambiguous evidence. Words and punctuation are preserved.
- A conservative marker check abstains on obviously corrupted submitter OCR.
- Every source-located result still requires semantic review.
- CLI commands for schema generation, intake, extraction, offline verification and API smoke testing.
- 132 automated tests passed, including mocked endpoints and local HTTP routes. These are engineering tests,
  not measured Apertus quality results.
- CSCS model-list authentication and a real Apertus 1.5 8B connectivity prompt passed.
- A real two-page Nidau PDF was extracted by Apertus 1.5 70B and visually inspected.
  Four fields were located after whitespace handling; the submitter was withheld for
  corrupt OCR, and three missing answer/decision fields remained null.
- A local review workbench: PDF upload, original page preview, page navigation,
  extracted text and highlighted source passages, explicit Apertus extraction,
  confirmation, corrections, reasoned absence and undo.
- Persistent SQLite review records and before/after audit history; a revision
  check prevents one review from silently overwriting another.
- Manual transcription from an original page is labelled as visual review, with
  a required note and no invented text offsets. Model suggestions are preserved.
- JSON export includes only explicit reviewer decisions and lists remaining
  unreviewed fields separately. The API key is never included in browser state.
- Explicit replay/live modes. Replay skips local credentials, disables live
  extraction server-side, verifies a bundled synthetic practice fixture and
  preserves its non-model/non-gold labels. It uses a separate default local store.
- Dockerfile with Python/Poppler/fonts, a narrow build context, Compose named
  review storage, localhost port publishing and health check; Makefiles in the
  selected project and repository root. Actual container build/run is pending.
- Clean-source startup check using only public source/sample files and installed
  Python dependencies; no private pilot copied and no model call required.
- Canonical full-request cache with checksums and atomic writes; failed/corrupt
  replay has no live fallback. Original completion time, usage and latency persist.
- Batch extraction preserves every selected manifest row, checkpoints per item,
  never edits the input manifest for limits, and supports matching-config resume.
- Cached batch import checks source/result/cache identity and reruns verification;
  repeated import preserves review decisions and adds no duplicate run.
- Gold export is read-only against the store, excludes synthetic/QA documents,
  refuses stale output directories and retains source rights/provenance. Uncertain
  OCR/language stays unreviewed rather than becoming an absent label.
- Fetch redirects are checked at every hop; partial fetch retries retain other
  corpus entries. New selections carry role-hint and government-level provenance.
- Browser checks on an isolated data directory passed: PDF preview, highlighted
  evidence, confirmation, rejected invented correction, supported correction,
  reload persistence, audit history and downloaded JSON. That export contained
  exactly two reviewed fields and six explicitly unreviewed fields. All test
  decisions were labelled **Automated UI QA — not gold labels**; the user's
  main workbench was not edited by those isolated interface checks. Existing
  decisions in the main store are recorded in the current update above. No
  additional real-model call was made during those interface checks.

## Next gate

CSCS is configured locally. The current default is the tested official
`swiss-ai/Apertus-v1.5-70B`. The first 8B runs failed strict validation; their raw
responses were preserved. One 70B example does not establish a general model
ranking or production accuracy. See [the pilot report](../../docs/12-cscs-pilot.md).

Real-response batching/caching is implemented and proven on a bounded DE/FR pair.
The next step is competent source review, metadata/role checks, a frozen split
and measured evaluation using the implemented scorer. The packaged Docker runner still needs an actual
container check. The practice fixture and workbench do not establish model accuracy.

## Remaining before submission

- License-checked real sample and source manifest; human-reviewed gold annotations.
- Reviewed controlled vocabularies and human-validated question/answer and affair links.
- Real multi-body reviewed comparison evidence; the scoped comparison software is implemented.
- Evaluation and baseline results, including coverage and semantic correctness.
- Build/run the implemented Docker package and verify volume persistence across rebuilds.
- Public repository and final technical report PDF, at most six pages.

The older Liebefeld specifications in the workspace are planning material. They
are not a statement of implemented features or the online submission requirements.
