# Skony - parliamentary data with proof

An **Apertus 1.5** project for **Hack Apertus online / Track 2A / OpenParlData**.
Deadline: **16 October 2026, 12:00 CEST / 15:00 Pakistan time**.

Skony investigates a shared representation for parliamentary requests and
government answers. Its prototype extracts eight raw fields, locates source
evidence and supports persistent human review. The target is a reusable converter
with measured findings across bodies and languages.

**Status, 16 October:** extraction/review, batch caching/checkpoints, saved-result
import, gold-export safeguards, replay/live modes and Docker packaging are
implemented. **131 tests** and a clean-source startup check pass. Two real DE/FR
PDFs replayed with identical results and **zero model calls**. Actual container
execution, reviewed-corpus evaluation and affair assembly remain pending.

## Direction and evidence

- [Implementation status](docs/BUILD_STATUS.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Running and updating, including Docker](docs/RUNNING.md)
- [Batch extraction and review workflow](docs/BATCH_EVALUATION.md)
- [Verification evidence and limits](docs/PIPELINE_VERIFICATION.md)
- [Measured results and honest limits](docs/RESULTS.md)
- [Active technical report draft](technical_report.md)

## Run the packaged version

From the repository root or this directory, use `make run`. Without Make, run
`docker compose up --build --wait --wait-timeout 90` from this directory.
Open [Skony](http://localhost:8765). Docker Engine/Desktop with Linux containers
and Compose v2 is required. The container build has not been verified here;
see the [running guide](docs/RUNNING.md) for prerequisites and exact status.

The default replay demonstration uses a bundled **synthetic practice document**
with authored suggestions, clearly labelled as neither Apertus output nor gold.
It makes no model call. Named volume storage is intended to preserve uploaded
PDFs, reviews and audit history when application files are rebuilt.

## Run with local Python

From track_2a/, with Python 3.11+ and the pinned dependencies:

~~~powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m skony serve --mode replay --port 8765
~~~

Open http://127.0.0.1:8765. Poppler's pdftoppm supplies original-page previews.
Replay documents and decisions persist in ignored output/workbench-replay/.
Use `--mode live` to open the existing output/workbench/ and local API setup.
See the development guide for configuration and isolated QA.

Live mode imports the privately retained pilot if present. The public replay
sample does not depend on it. Explicit live extraction uses LLM_NAME,
LLM_BASE_URL and LLM_API_KEY. Keep keys outside the public package. Replay blocks
live extraction even when credentials exist; no silent model fallback is used.

~~~powershell
python -m unittest discover -s tests
~~~

**131 engineering tests passed on 16 October 2026.** They do not establish real
model accuracy or multilingual coverage.

## Judge execution: required, still pending

The [official template](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md)
requires Docker execution through make run from the selected project root.
Keep track_2a/. Dockerfile/Compose/Makefiles and the public practice seed now
exist. Clean-source startup, previews and restart persistence pass with local
Python dependencies; Docker build/run/rebuild verification remains pending.
Run `python scripts/check_docker.py` on an engine host for the full check.
Real-response batching/caching works; human review and scoring are next.

## Source data and limitations

The private corpus has 44 downloaded PDFs and one preserved failed download.
Two DE/FR PDFs now have cached real Apertus responses, in addition to the older
Nidau pilot. Redistribution rights and a frozen reviewed evaluation set are
pending; the bundled synthetic fixture is an engineering demonstration only.
The selected data/ directory must remain <=100 MB.

Automatic evidence currently represents one page/quote per field. Source
matching does not establish correct roles or complete answers. Textless scans,
long inputs, tables and annexes need explicit unsupported/review handling.
No new OCR pipeline is implemented.

## Submission and licensing

Submit through the [organiser website](https://hackapertus.ch/online-hack/submissions),
selecting Track 2A - OpenParlData: public GitHub repository with converter,
Apertus prompts, validator and README samples; technical report PDF **<=6 pages**.
The report opens with a judging-criteria → evidence map so reviewers can
verify each claim where it lives.

The [event terms](https://hackapertus.ch/terms-and-conditions) specify Apache-2.0
for code/weights, CC-BY-4.0 for non-code output and CDLA-Permissive-2.0 for
submitted datasets, subject to stated exceptions and third-party rights.
Document item-level publication rights and supporting development models.

| Component | Licence | Note |
|---|---|---|
| Application code (this repository) | Apache-2.0 | per event terms; `LICENSE` at root and in `track_2a/` |
| Documentation and technical report | CC-BY-4.0 | per event terms |
| Bundled synthetic fixture (`data/sample/`) | CDLA-Permissive-2.0 | authored for Skony; fictional people and parliament |
| Runtime dependencies: pydantic 2.13.4, httpx 0.28.1, pypdf 6.11.0 | MIT / BSD-3-Clause | pinned in `requirements.txt`; check each package's `LICENSE` before redistribution |
| Apertus v1.5, used at development time via the CSCS endpoint | Apache-2.0 (model) | not redistributed; the extraction prompt is in `src/prompts/extract.txt` |
| OpenParlData source PDFs (private corpus) | source-specific terms | item-level rights unverified; **not redistributed** in this repository |
| Container base (`python:3.11-slim`, Poppler) | Debian package terms | used only to build the runner image |
