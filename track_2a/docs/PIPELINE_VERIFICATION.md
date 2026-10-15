# Pipeline verification — 15 October 2026

These are engineering checks. They do not establish extraction accuracy,
semantic correctness, reviewer competence or redistribution rights.

| Check | Observed result |
|---|---|
| Local regression suite | **82 tests passed**, Python 3.11, 13.289 seconds. |
| Frontend/Python syntax | JavaScript syntax check and Python compilation passed. |
| Clean public source start | Passed without local credentials or private pilot files. PDF/page-image preview, review, restart persistence, export and replay rejection of live calls passed. |
| Existing corpus | All **44 downloaded PDFs** parsed and matched their manifest hashes. One failed-fetch row remains in the 45-row manifest. Some sources emit PDF repair warnings; parsing is not a visual correctness check. |
| Real Apertus batch | Approved DE file `743_924676.pdf` and FR file `6621_923197.pdf` succeeded using `swiss-ai/Apertus-v1.5-70B` at CSCS. The existing failed-fetch row was retained. |
| Offline real-response replay | **2 cache hits, 0 model calls**, empty API credential and a transport that rejects any HTTP attempt. Verified result objects matched the original run. The failure row and input manifest were preserved. |
| Workbench import | Both cached results imported into the existing store without new inference. Repeating import left the full store unchanged and preserved **12 existing field decisions**. |
| Existing review export | One document has eight decisions and passes the mechanical export gate; 44 are incomplete. Its source language is unknown in metadata. Export was written only to private verification output with an explicit competence/semantic-review limitation. This is not a frozen evaluation gold set. |
| Docker execution | **Unavailable**: Docker CLI/engine absent; WSL also not installed. No container build/run passed here. `check_docker.py` records this accurately and is ready for a Docker-enabled host. |

The approved live calls reported 2,460 prompt tokens and 1,493 completion
tokens, **3,953 total**. Original call latencies were **13.594 s** (DE) and
**9.406 s** (FR). Replay preserves those original observations rather than
replacing them with zero. No currency cost or corpus-quality score is inferred.
The replay proof completed at 02:54:44 UTC / 07:54:44 Pakistan time.

Private evidence, relative to `track_2a/`:

- `output/pipeline-proof-20261015/proof.json`
- `output/pipeline-proof-20261015/first/run_ledger.json`
- `output/pipeline-proof-20261015/replay/run_ledger.json`
- `output/cache/` — checksummed effective requests and raw responses.
- `output/verification/unit-tests.log`
- `output/verification/corpus-import.json`
- `output/verification/workbench.json`
- `output/verification/gold-export-20261015/manifest.json`
- `output/docker-check/report.json`

These paths are ignored local artifacts. Source texts and responses are not
approved for public packaging merely because they were processed here. The two
live calls ran only after explicit user approval for those PDFs and CSCS.

## Review of the added tools

The existing selector, fetcher, cache, batch runner, importer, gold exporter and
annotation guide were retained as the starting point. Fixes made in this pass:

- Cache identity now includes the actual effective messages/schema/parameters,
  endpoint, parser and optional model revision. API-key rotation does not miss
  cache; verifier changes rebuild checks from the same raw response.
- Cache integrity failures stop visibly. Atomic replacement protects previous
  entries; a corrupt record never silently triggers a paid live fallback.
- Batch limits do not edit the manifest. Downloads that failed, missing/tampered
  files, API failures and invalid model output stay in the ledger. Checkpoints,
  matching-config resume and archived attempts preserve interrupted work.
- Usage and original latency remain attached to both successful and
  schema-invalid completed responses; actual request attempts count even when
  the endpoint fails. Missing usage is reported as unknown.
- Saved batch suggestions import with checksums and re-verification, without
  overwriting human decisions or duplicating a run.
- Fetch redirects are checked at every hop. Unsafe filenames/URLs are rejected;
  partial retries preserve unselected manifest entries. Role/level provenance
  is carried forward, with heuristic roles explicitly requiring review.
- Gold export excludes synthetic/practice and automated-QA documents, opens
  the review store read-only, preserves source provenance, refuses a nonempty
  output directory, and lists exact record checksums in its manifest.
- The annotation guide now distinguishes absence from uncertainty. Unreadable
  OCR or uncertain language leaves a field unreviewed. Existing user decisions
  were preserved; they were not silently relabelled.
- The Docker build context now includes the script entry points used by the
  expanded tests. Its new verifier checks an isolated Compose project, original
  preview, nonroot operation and persistence across recreation on an engine
  host; it removes only its disposable QA resources.

Next work: complete competent source review and language/role metadata, freeze
affair-disjoint development/evaluation groups, implement the deterministic
scorer and comparisons, and run the Docker verifier. No human annotation was
created by the automated pipeline proof.
