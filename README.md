# Skony — parliamentary affairs from PDFs, with proof

**Hack Apertus online · Track 2A · OpenParlData.** Submission: 16 October 2026.

Skony investigates whether parliamentary affairs (motions, postulates,
interpellations, written questions) from different Swiss parliaments can share
one structured representation — and builds an **Apertus v1.5** pipeline that
extracts that representation from real parliamentary PDFs with **page- and
span-level provenance**: every extracted value keeps its page number, original
quote and character offsets, so a reviewer can verify it against the source in
seconds. Unsupported values are withheld, not guessed.

## Run it

```bash
make run          # Docker; judges' entry point — from this root
```

Then open http://localhost:8765. The default replay demo uses a bundled
synthetic practice document (clearly labelled, no API key, no model call).
Without Make: `docker compose up --build --wait --wait-timeout 90` from
`track_2a/`. Live Apertus extraction is configured with `LLM_NAME`,
`LLM_BASE_URL`, `LLM_API_KEY` (see `track_2a/.env.example`).

## Where things are

| Path | What it is |
| --- | --- |
| `track_2a/` | **Project root** (per the Hack Apertus template): converter, prompts, validator, review workbench |
| `track_2a/README.md` | Full project documentation, status and limitations |
| `track_2a/technical_report.md` | Technical report (source of the submitted ≤6-page PDF) |
| `track_2a/src/skony/` | PDF intake → Apertus client → strict validation → evidence verification → review store |
| `track_2a/src/prompts/extract.txt` | The Apertus extraction prompt |
| `track_2a/docs/` | Architecture, verification evidence, batch/evaluation workflow, annotation guide |
| `track_2a/data/sample/` | Public synthetic practice fixture (authored; not model output, not gold data) |
| `track_2a/tests/` | Engineering test suite (`python -m unittest discover -s tests`) |

## Status in one paragraph

The PDF→schema slice, provenance verification, human-review workbench, batch
caching with replay, and Docker packaging are implemented and covered by 82
passing engineering tests; a real DE/FR document pair was extracted with
Apertus 1.5 70B and replayed with identical results and zero model calls.
Gold-set annotation, measured evaluation, controlled-vocabulary mapping and a
cross-parliamentary comparison are this submission's evidence work — see
`track_2a/technical_report.md` for exactly what is measured, what is partial,
and what is not yet done. The container build is packaged but was not
executable in the development environment; `track_2a/scripts/check_docker.py`
verifies it on any Docker host.

## License

Code: Apache-2.0 (`LICENSE`). Documentation and reports: CC-BY-4.0.
The bundled practice fixture is authored by the project and reusable under
CC-BY-4.0. No third-party parliamentary documents are redistributed in this
repository; the pipeline fetches public sources by manifest.
