# Skony - parliamentary data with proof

The [B1–B7 evaluation implementation guide](docs/EVALUATION_IMPLEMENTATION.md)
documents acquisition gates, independent relation review/scoring, metadata
comparison, reviewer checks, feasibility findings and frozen B0/B1/B2 runs.
Its real-corpus preflight preserves missing human evidence rather than declaring
an accuracy benchmark complete.

An **Apertus 1.5** project for **Hack Apertus online / Track 2A / OpenParlData**.
Deadline: **16 October 2026, 12:00 CEST / 15:00 Pakistan time**.

Skony investigates a shared representation for parliamentary requests and
government answers. Its prototype extracts eight raw fields, locates source
evidence and supports persistent human review. Its `/explore` research interface
searches original PDFs and opens source-linked dossiers with requests/answers,
dated events and submitter blocks, plus cited JSON/CSV briefs. The target is a reusable converter
with measured findings across bodies and languages.

**Status, 16 October:** extraction/review, batch caching/checkpoints, saved-result
import, replay/live modes and Docker packaging are implemented. The v0.2 layer
adds scoped affairs/core-field review, immutable offline comparisons, migration,
gold eligibility/scoring and three citation capabilities at `/scoped`. A
controlled-vocabulary layer (`skony.vocab`, 33 terms, 229 aliases, DE/FR/EN)
now maps raw labels to stable affair-type/role/state/outcome IDs with
Akoma Ntoso/Popolo/OParl/eCH alignment; mappings are versioned,
MappingRule-compatible and never overwrite raw values. A structural
inventory (`skony.structure`, census in docs/STRUCTURE.md) detects annexes,
embedded images and table regions corpus-wide with provenance — inventory,
not interpretation.
**245 Python engineering tests and 16 interface-controller tests** pass. Two previously processed real DE/FR PDFs replayed
with identical results and **zero model calls**. Actual container execution,
human gold evaluation, semantic extraction accuracy and relation review remain
pending. The main extraction screen still uses v0.1; v0.2 HTTP extraction imports
recorded output. New v0.2 fixtures and browser checks are synthetic.

## Direction and evidence

- [Measured checks, private pilot observations and reproduction limits](docs/RESULTS.md)
- [Public data and secret handling](docs/PUBLICATION.md)

- [Project direction and requirements](../../docs/16-project-direction.md)
- [Source register](../../docs/17-source-register.md)
- [Delivery backlog and release gates](../../docs/18-delivery-backlog.md)
- [Implementation status](docs/BUILD_STATUS.md)
- [A1–A7 implementation contracts and commands](docs/AUDIT_IMPLEMENTATION.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Affairs explorer: search, dossiers, timeline and research exports](docs/EXPLORER.md)
- [Running and updating, including Docker](docs/RUNNING.md)
- [Batch extraction and review workflow](docs/BATCH_EVALUATION.md)
- [Controlled vocabularies and standards mapping](docs/VOCABULARY.md)
- [Structural content inventory: annexes, images, tables](docs/STRUCTURE.md)
- [Verification evidence and limits](docs/PIPELINE_VERIFICATION.md)
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
Use [the affairs explorer](http://127.0.0.1:8765/explore) to search and read the
collection, or the document review screen to add PDFs and run extraction.
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

**245 Python engineering tests and 16 interface-controller tests passed on 16 October 2026.** Run
`node --test tests/evidence-ui.test.cjs tests/explorer-ui.test.cjs tests/scoped-ui.test.cjs` for the controller checks.
They do not establish real
model accuracy or multilingual coverage.

## Judge execution: required, still pending

The [official template](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md)
requires Docker execution through make run from the selected project root.
Keep track_2a/. Dockerfile/Compose/Makefiles and the public practice seed now
exist. Clean-source startup, previews and restart persistence pass with local
Python dependencies; Docker build/run/rebuild verification remains pending.
Run `python scripts/check_docker.py` on an engine host for the full check.
Real-response batching/caching and the field scorer work; competent human gold
annotation and measured evaluation are next.

## Source data and limitations

The private corpus has 44 downloaded PDFs and one preserved failed download.
Two DE/FR PDFs now have cached real Apertus responses, in addition to the older
Nidau pilot. Redistribution rights and a frozen reviewed evaluation set are
pending; the bundled synthetic fixture is an engineering demonstration only.
The selected data/ directory must remain <=100 MB.

The main v0.1 extraction workflow represents one page/quote per field. The v0.2
contract retains ordered multi-page segments and typed structural proposals;
human relation review and relation accuracy remain unsupported/untested. Source
matching does not establish correct roles or complete answers. Textless scans,
long inputs and table/annex *content* need explicit unsupported/review handling;
their presence and location are inventoried (see docs/STRUCTURE.md).
No new OCR pipeline is implemented.

## Submission and licensing

Submit through the [organiser website](https://hackapertus.ch/online-hack/submissions),
selecting Track 2A - OpenParlData: public GitHub repository with converter,
Apertus prompts, validator and README samples; technical report PDF **<=6 pages**.
The Markdown report is still a draft.

The [event terms](https://hackapertus.ch/terms-and-conditions) specify Apache-2.0
for code/weights, CC-BY-4.0 for non-code output and CDLA-Permissive-2.0 for
submitted datasets, subject to stated exceptions and third-party rights.
Document item-level publication rights and supporting development models.
