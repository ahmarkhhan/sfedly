# Results — 16 October 2026

Current public checks and previously recorded private pilot observations are
separated below. The public commands reproduce engineering checks and the
synthetic replay; private pilot inputs and cache responses are not bundled. These are **engineering and provenance results**: they show that the
private pilot pipeline replayed recorded Apertus output with zero model
calls, and where its evidence checks abstain or reject. **They do not
establish extraction accuracy** — no human-reviewed gold set exists yet
(see «Honest limits»).

## Reproduce (public source, no credentials, no Docker)

From `track_2a/`:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests   # 245 engineering tests, no model calls
node --test tests/evidence-ui.test.cjs tests/explorer-ui.test.cjs tests/scoped-ui.test.cjs
python scripts/check_clean_start.py     # clean public copy: preview, review, export, replay guard
python -m skony serve --mode replay --port 8765
```

Replay mode verifies the bundled synthetic fixture hashes, applies the real
evidence verifier, and refuses live extraction even when credentials exist.
These offline checks and replay mode make no model calls. Install dependencies
first; installation needs internet access. The clean-start verifier also needs
Poppler for page previews.

| Check | Observed result |
|---|---|
| Local regression suite | **245 Python tests and 16 interface tests passed**, Python 3.11 / Node 24, 16 October 2026 |
| Clean public-source start | Preview, review, restart persistence, export and replay rejection of live calls pass without credentials or private files |
| Private corpus integrity | 44 of 45 manifest rows parse with matching pinned hashes; row 45 is a preserved failed download |
| Docker execution | **Not verified here** (no Docker/WSL on the build host); `scripts/check_docker.py` and CI are ready for an engine host |

## Measured runs

### 1. Bounded real extraction + offline replay (15 October 2026)

One approved DE source (`743_924676.pdf`) and one FR source
(`6621_923197.pdf`) were processed once by `swiss-ai/Apertus-v1.5-70B` at
CSCS, then replayed offline with `scripts/check_batch_replay.py`. The source
PDFs are private and are not redistributed in this repository.

| Metric | First run (live) | Second run (replay) |
|---|---|---|
| Model calls | 2 | **0** |
| HTTP attempts | 2 | 0 — empty credential, transport rejects any HTTP attempt |
| Reported tokens (prompt / completion / total) | 2,460 / 1,493 / **3,953** | preserved from the original run |
| Latency per call | 13.594 s (DE) · 9.406 s (FR) | original observations preserved |
| Verified result objects | — | **identical to the live run** |
| Failed-fetch ledger row | preserved | preserved |

Importing both cached results into the existing workbench made no new
inference; a repeated import left the full store unchanged and preserved all
**12 existing human field decisions** across four documents.

### 2. Scanned-document pilot: Nidau postulate

One scanned postulate with an existing OCR text layer, replayed from the
recorded response with `scripts/replay_pilot.py` (no new inference):

| Model | Outcome |
|---|---|
| Apertus-v1.5-8B (two attempts) | Both responses rejected by strict validation: one copied the JSON schema instead of the document, one mixed null values with evidence quotes |
| Apertus-v1.5-70B | Valid extraction; 7.234 s, 1,725 tokens; verifier `evidence-v0.2` located **4 of 8 fields** |

Field-level outcome of the accepted 70B response:

| State | Fields |
|---|---|
| `source_located` (quote found, offsets recorded; still requires review) | `title`, `affair_type_raw`, `submitted_date_raw`, `question_text` |
| Abstained | `submitter_raw` — conservative marker check flagged obviously corrupt OCR |
| Null (absent in source) | `answer_text`, `decision_raw`, `decision_date_raw` |

These are single-call observations, not a benchmark and not a model ranking.

## What failed — kept visible, not filtered out

- The two 8B responses above failed strict validation; the raw responses are
  preserved alongside the accepted one.
- One corpus fetch row has failed since download and remains in every 45-row
  manifest and ledger; batch limits never edit it out.
- Several sources emit PDF repair warnings on parse; parsing is not a visual
  correctness check.
- Corpus metadata covers 24 DE, 8 FR and 13 unknown-language rows; roles are
  heuristic hints until reviewed.
- A corrupt cache entry stops the run visibly; it never silently triggers a
  paid live fallback.

## Review and gold-set state

The store holds 12 human field decisions across four documents. One document
passes the eight-decision mechanical export gate; its source language is
unknown in metadata, and reviewer competence and semantic accuracy are not
certified. **This is not a frozen evaluation gold set.** The gold column of
any accuracy table is therefore pending by design: field precision/recall,
abstention coverage and a baseline comparison remain planned work
(see `technical_report.md`, «Planned evaluation»).

## Honest limits

- The bounded DE/FR batch contains two real documents; the earlier scanned
  Nidau pilot is recorded separately above. These are small selected pilots,
  and both were selected by the team. Nothing here measures accuracy on
  unseen documents.
- `source_located` means a string was found in the unchanged page text; it
  does not establish correct semantic assignment — every located field still
  requires human review.
- The 245 Python and 16 interface tests are engineering tests (mocked transports, synthetic
  fixtures). They protect the pipeline; they say nothing about model quality.
- One 8B failure pair and one 70B success on a single scanned document do
  not rank models.
- The bundled `data/sample/` fixture is authored practice data — neither
  model output nor gold — and is labelled as such everywhere it appears.
