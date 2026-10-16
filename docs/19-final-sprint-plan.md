# Final sprint plan — Skony, Track 2A

Deadline: **16 Oct 2026, 12:00 CEST = 15:00 PKT**. Written 16 Oct, ~02:15 PKT.
Status basis: BUILD_STATUS.md, PIPELINE_VERIFICATION.md, two judge audits (15–16 Oct).

---

## Part 1 — What the project is and does right now

**One line:** Skony converts parliamentary affair PDFs into a shared, comparable
schema using Apertus 1.5, where every extracted value must carry verifiable
source evidence — and everything that can't be verified is abstained on, not
guessed. It answers the Track 2A question: *is a common schema for parliamentary
affairs feasible across bodies and languages, and where does it break?*

**Working pipeline today:**

1. **Intake** — PDF → per-page original text, page numbers, SHA-256 digest,
   textless-page flags. 44 corpus PDFs hash-verified (1 preserved failed fetch).
2. **Extraction** — Apertus 1.5 (8B/70B via CSCS) with a schema-constrained
   prompt demanding original wording + quote on the claimed page. Strict JSON
   validation; 8B failed it, 70B passed.
3. **Verification** — quote → character-offset resolution into the unchanged
   page text; fabricated, missing or ambiguous evidence rejected; corrupt
   submitter OCR auto-abstained. `source_located` ≠ semantically correct.
4. **Review workbench** — local web UI: original page images, highlighted
   evidence spans, confirm / correct / explicit-absent / undo; decisions in
   SQLite with before/after audit; visual transcriptions labelled with no
   invented offsets; reviewed-only export. 12 human field decisions, 4 docs.
5. **Batch + cache** — canonical request-hash cache (endpoint + parser + model
   revision), atomic writes, corrupt cache never triggers a paid live fallback.
   Real DE+FR pair extracted by 70B (2 live calls, 3,953 tokens, 13.6s/9.4s),
   replayed offline with 2 cache hits / 0 calls / HTTP disabled.
6. **v0.2 contracts layer** — content-addressed object store, digest-verified
   migration (all 12 legacy decisions preserved), JSON schemas for gold / review /
   run / comparison, and `comparison.py`: offline, snapshot-pinned cross-scope
   comparison queries with per-field citations and mapping-compatibility caveats.
7. **Proof & honesty layer** — 82 engineering tests; clean-start check without
   keys; gold export (read-only, excludes synthetic/QA docs, provenance manifest);
   annotation guide distinguishing *absent* from *uncertain*; every doc states
   what is measured vs. what is engineering-only.

**Honestly not done:** no git repo; Docker packaged but never executed (no
engine on this host); scorer not implemented; no human-reviewed gold set beyond
4 docs; no cross-parliament comparison *results*; no report PDF; two `.env`
files with a live key sitting in `track_2a/`.

---

## Part 2 — Sprint steps, in order

Time budget: 13h wall, ~10h usable. **Do not reorder.** Each step names its
exit test. If a step overruns its box by >50%, cut scope inside the step —
never skip a gate.

### Gate A — Admissibility (02:15 → 04:30) — NOTHING SHIPS WITHOUT THIS

- **A1. Rotate the CSCS key** (15 min). Assume both `.env` files are
  compromised-in-waiting. New key into `.env`, verify with one smoke prompt.
- **A2. git init + clean tree** (30 min). `.gitignore` must cover `.env`,
  `" (2).env"`, `data/private/`, `output/`, `*.sqlite3`, `__pycache__`.
  `git status` must show zero secrets before first commit. Delete `" (2).env"`.
- **A3. Apply the HackApertus project-template structure** (30 min): their
  README skeleton, LICENSE (Apache-2.0 already present), top-level layout.
- **A4. Private→public boundary** (30 min). Move `data/sample/contracts-v0.2/`
  (synthetic, authored, already labelled non-gold) into the repo; keep all real
  PDFs, the Nidau pilot, and the review DB out. Write `data/README.md` stating
  exactly what is public, what is excluded, and why (source licences pending).
- **A5. Push to GitHub** (15 min). Public repo. Commit trailer as required.
- **Exit test:** fresh-clone on a second directory → `python -m pytest` passes
  (or the documented subset) → no file in the repo contains a key or a real
  parliamentary PDF.

### Gate B — Measure (04:30 → 09:00) — WHERE ALL INSIGHT POINTS LIVE

- **B1. Human gold reviews, 8 docs minimum** (3h, the long pole — start first,
  coffee, no code). Target mix: 3 DE bodies incl. Nidau + 1 cantonal + 1
  federal, 2–3 FR, 2 government levels, ≥1 scan. Use the annotation guide;
  uncertain OCR/language = leave unreviewed, never force a label.
  *Cut-line: if time collapses, 6 docs with both languages beats 8 without FR.*
- **B2. Scorer script** (1h). Read-only over the review store → per-field
  decision matrix: value correct / corrected / absent-correct / absent-wrong /
  unreviewed, per document. Output NDJSON + a Markdown table. No ML, no LLM —
  deterministic, rerunnable, in-repo.
- **B3. Baseline** (45 min). Regex/keyword extractor: dates, affair-type
  keywords (Motion/Postulat/Interpellation + FR equivalents), first-heading
  title. Same scorer. This is the honest comparison the track asks for.
- **B4. Comparison run** (30 min). Point `comparison.py` at the real reviewed
  scopes; freeze a snapshot; export the cross-body field matrix (fields ×
  body/language cells with ✓/⚠️/✗/absent/not-present).
- **Exit test:** one committed `results/` folder containing scorer output for
  baseline vs. Apertus-70B vs. Apertus+verifier, and the comparison matrix —
  regenerated by one documented command from a clean checkout (replay mode,
  no key).

### Gate C — Report (09:00 → 12:00)

- **C1. Report, ≤6 pages → PDF** (2.5h). Structure: (1) question + why
  evidence-forced abstention is the right design for parliamentary data;
  (2) pipeline + review architecture, one diagram; (3) the matrix + baseline
  table + failure taxonomy with 5–8 real examples (garbled OCR, scans, Q/A
  pairing across pages, FR layout); (4) the feasibility answer — which fields
  are safe to automate, which need review UI, where the schema cannot represent
  the source; (5) limits + reproducibility (replay command, no key needed).
  Partial and negative findings are explicit success criteria — say so.
- **C2. README final pass** (30 min): judge quick-start at top, the one replay
  command, the results table, honest status block.
- **Exit test:** PDF renders ≤6 pages; every number in it traces to a committed
  `results/` artifact.

### Gate D — Submit + Docker (12:00 → 14:15)

- **D1. Docker.** No engine on this machine — so: (a) find any Docker host
  (other machine, colleague, cloud VM); run `check_docker.py` + compose up,
  verify replay demo + volume persistence (1h). (b) If genuinely impossible by
  12:30: state it plainly in README + report ("packaged and verifier included;
  engine unavailable during the event"), and make the **keyless replay demo via
  `python -m skony`** the documented judge path. Honesty over theatre.
- **D2. Submission form** at hackapertus.ch/online-hack/submissions (45 min):
  repo URL, PDF upload, 3-line summary naming insight + breadth + replay demo.
- **D3. Buffer + final commit/tag** `submission-v1.0` (30 min).

### Hard rules for the day

1. **No new subsystems.** v0.2 shipped tonight; anything new now is risk, not
   points. Fixes only.
2. **Reviews before code.** B1 is the only step that cannot be compressed or
   faked; it gates B2–B4, C1, and the entire Insight score.
3. **Every claim in the report links to a committed artifact.** This is already
   the project's voice — keep it.
4. **The flaky test** (`test_mutation_requires_token_and_matching_origin`):
   15-minute look; else mark xfail with a note. Do not bleed time.
5. If 12:00 arrives mid-C: PDF first, polish never.

**Target:** 76–82/100 — admissible, measured, honest, reproducible.
