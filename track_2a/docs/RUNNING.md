# Running and updating Skony

The default **replay mode** opens a bundled practice document and exercises
source verification and human review without an API key. The document and
suggestions are synthetic authored examples, not an Apertus run or gold data.
The interface and exports keep that distinction visible.

## Docker entry point

Prerequisites: Docker Engine/Desktop with Linux containers, Docker Compose v2
supporting `up --wait`, and GNU Make if using the Makefile. Initial image build
needs internet access for the Python image, packages and Poppler. Local model
weights and a GPU are not required for this offline practice workflow.

From the repository root or from `track_2a/`:

```text
make run
```

If Make is unavailable on Windows, open PowerShell in `track_2a/` and use:

```powershell
docker compose up --build --wait --wait-timeout 90
```

Open [Skony](http://localhost:8765). The image contains pinned Python
dependencies, Poppler and a public synthetic fixture. Private data, local env
files and previous workbench output are excluded from the build context.

**Verification status:** [engineering checks](https://github.com/ahmarkhhan/sfedly/actions/runs/38883803672)
and [Docker verification](https://github.com/ahmarkhhan/sfedly/actions/runs/38883803830)
passed on 16 October 2026, including container startup, PDF/image previews and
review persistence across rebuilding. Earlier local checks lacked Docker/WSL;
the linked CI run provides the container execution evidence.
On an engine host, run `python scripts/check_docker.py` (or `make verify-docker`).
It builds/tests an isolated QA project, checks original PDF/image preview and
review persistence across rebuilding/recreation, then removes its own QA volume.
It uses no credentials/private PDFs and leaves the normal workbench volume alone.
The report is saved under `output/docker-check/`.

## Keep developing normally

1. Edit Python, HTML, CSS or JavaScript in the existing source files.
2. Run `make run`, or the Compose command above, again.
3. Compose rebuilds/recreates the application using the latest files.

Uploaded documents, decisions and audit records live in the named `review-state`
volume at `/state`, separate from application files. Standard rebuilds and
`make down` preserve that volume. Avoid removing the volume if you need its data.
Dependencies change in `requirements.txt`; ordinary source edits need no Docker
configuration change. [Compose recreation](https://docs.docker.com/reference/cli/docker/compose/up/),
[volume lifecycle](https://docs.docker.com/engine/storage/volumes/)

```text
make test   # build image and run the engineering suite
make logs   # application logs
make down   # stop/remove containers; keep named review storage
```

Equivalent commands from `track_2a/`:

```powershell
docker compose build workbench
docker compose run --rm --no-deps -e LLM_API_KEY= workbench python -m unittest discover -s tests
docker compose logs --follow workbench
docker compose down
```

Change the published port with `SKONY_PORT`. The internal port remains 8765;
the explicit public-port option retains localhost Host/Origin checks.

## Opt into live Apertus

Copy `.env.example` to `.env` and fill in your endpoint/key. Compose reads this
file at runtime; it is excluded from the image. Set `SKONY_MODE=live` when ready
to permit explicit **Extract with Apertus** actions. Re-run the launch command.
Starting the application does not itself call the model.

The bundled synthetic demo is not a real recorded Apertus response. The older
real Nidau pilot remains private and is not packaged. Add real, rights-checked
documents for development and complete a separate human-reviewed corpus.

## Local Python development

Use Python 3.11+ and Poppler on PATH:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m skony serve --mode replay --port 8765
```

Default replay storage is `output/workbench-replay/`. The existing main
`output/workbench/` remains the live-development store. To open it with the
existing private pilot and API configuration:

```powershell
python -m skony serve --mode live --port 8765
```

Use `--data-dir` or `SKONY_DATA_DIR` to select another store. Shell environment
variables and CLI options select the local execution mode; the local `.env`
loader reads only `LLM_*` variables in live mode. Replay skips that file.

## Checks completed in this workspace

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests
python scripts/check_clean_start.py
```

The clean-source check uses a temporary public-source copy and the installed
Python dependencies. It verifies startup without credentials/private pilot,
original PDF/image access, a review, restart persistence, export and rejection
of live extraction. Its decisions are explicitly automated QA, not gold. It
does not modify either existing user workbench and is not a Docker build test.

The batch runner/cache now supports real Apertus responses, visible failures,
checkpoint/resume and saved-result import. The approved DE/FR proof replayed
with two hits and zero calls. Use the [batch guide](BATCH_EVALUATION.md) and
[verification report](PIPELINE_VERIFICATION.md). Complete human annotations and
evaluation remain in the [delivery backlog](../../docs/18-delivery-backlog.md).
