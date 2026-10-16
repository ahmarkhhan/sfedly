# Devpost «Additional info» — judging criteria map (paste-ready)

Mirrors the table at the top of `technical_report.md`. Devpost markdown table
support is unreliable; paste as this list. Keep in sync with the report.

---

**Judging criteria → where the evidence lives** (repo: github.com/ahmarkhhan/sfedly, `track_2a/`)

**Insight** (main criterion: a well-founded conclusion on common-schema feasibility; partial or negative counts)
→ "Honest limits" section of the technical report + docs/RESULTS.md.
Partial conclusion: a common raw-field representation proved feasible for the eight-field slice tested (fields located with original wording and spans across one DE municipal and one FR cantonal document); the unresolved seam is question/answer pairing and role assignment across bodies.

**Breadth** (document types, languages, levels of government)
→ docs/RESULTS.md "Measured runs" + corpus integrity table in docs/PIPELINE_VERIFICATION.md.
Narrow but real: DE + FR, two bodies (Nidau municipal, Genève cantonal), born-digital plus one scanned/OCR-layer document; 44-PDF hash-verified corpus awaiting review. 245 Python and 16 interface engineering tests.

**Traceability and faithfulness** (no invented values; span-level provenance; flag rather than guess)
→ src/skony/verify.py: every non-null field carries document ID, page, original quote and character offsets; fabricated or unlocatable evidence is rejected; unverifiable values abstain instead of guessing (tests/test_evidence.py).

**Built with Apertus**
→ src/prompts/extract.txt; recorded swiss-ai/Apertus-v1.5-70B runs at CSCS with token and latency observations (docs/RESULTS.md). Development-time only, not redistributed.

**Reusable outputs** (public repo: converter, prompts, validator, README samples)
→ 3-command reproduce path in docs/RESULTS.md — after dependency installation, public synthetic replay needs no credentials or model calls; hash-checked synthetic sample in data/sample/. The real DE/FR cache replay needs private inputs.

**Judge execution** (make run / Docker)
→ root + track_2a Makefile, Dockerfile (non-root, healthcheck), compose.yaml, scripts/check_docker.py, CI workflow docker-verify.yml.
Honest state: packaged but unverified on the development host (no Docker/WSL there); the clean public-source start passes outside a container.

**Honest limits (the insight contribution, verbatim from the report):** two documents are not coverage; prompt and verifier were tuned in-sample; no competence-checked gold set exists, so no precision/recall is claimed; "source located" proves a string match, not semantic assignment; Docker is packaged, not proven; one previously flaky test is named in the report; corpus roles/languages are heuristic until reviewed; conservative matching has blind spots — accepted as the price of never guessing.
