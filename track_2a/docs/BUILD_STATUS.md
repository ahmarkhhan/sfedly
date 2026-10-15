# Build status — 15 October 2026

Target: Hack Apertus **online**, Track 2A / OpenParlData. Deadline: 16 October,
12:00 CEST = **15:00 Asia/Karachi**. This is a starter, not a complete submission.

Current design authority: [project direction](../../docs/16-project-direction.md).
Implementation priorities and acceptance evidence are in the
[delivery backlog](../../docs/18-delivery-backlog.md); sources are in the
[source register](../../docs/17-source-register.md). These documents distinguish
official requirements from our internal targets and future features.

**Current update, 15 October:** **82 local tests pass**. The added corpus/cache/
batch/import/export tools were checked and hardened; see the
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
The workspace is not currently a Git checkout. The scorer is still pending.

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
- 82 automated tests passed, including mocked endpoints and local HTTP routes. These are engineering tests,
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
and deterministic evaluation. The packaged Docker runner still needs an actual
container check. The practice fixture and workbench do not establish model accuracy.

## Remaining before submission

- License-checked real sample and source manifest; human-reviewed gold annotations.
- Controlled vocabularies and question/answer linkage beyond this raw-field slice.
- Comparison over reviewed records across multiple parliamentary bodies.
- Evaluation and baseline results, including coverage and semantic correctness.
- Build/run the implemented Docker package and verify volume persistence across rebuilds.
- Public repository and final technical report PDF, at most six pages.

The older Liebefeld specifications in the workspace are planning material. They
are not a statement of implemented features or the online submission requirements.

