# Extraction and review workbench

For the current scope and upcoming build order, use the
[project direction](../../docs/16-project-direction.md) and
[delivery backlog](../../docs/18-delivery-backlog.md). The commands below describe
local development; the [running guide](RUNNING.md) documents Docker packaging,
replay mode, persistent storage and the remaining container verification gate.
Use [batch evaluation](BATCH_EVALUATION.md) for cached model execution, saved-result
import and gold export; [verification status](PIPELINE_VERIFICATION.md) records
the completed DE/FR replay proof and remaining limits.

Run commands from `D:\development\Skony\track_2a` with Python 3.11 or later.
The tested dependencies are pinned in `requirements.txt`. The current configured
model is official Apertus 1.5 70B at CSCS, following a successful document pilot.

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m skony schema --output docs/candidate.schema.json
```

## Open the review workbench

```powershell
$env:PYTHONPATH = 'src'
python -m skony serve --mode live --port 8765
```

Open `http://127.0.0.1:8765`. The server binds only to this computer. It loads
the configured `.env`; the browser never receives the key. Reviews and copied
PDFs are saved under ignored `output/workbench/`. Stop it with Ctrl+C.

The locally retained real Nidau pilot is imported if its PDF and verified result
exist; it is labelled **Recorded Apertus extraction** and starts unreviewed.
It does not make another model call on startup. On a clean checkout, add a PDF
and choose **Extract with Apertus**. No private pilot documents are required.

Inspect source passages and the original page before confirming a suggestion.
For a text correction, copy the value and passage from the selected page. If
OCR is unclear, choose **Original page image** and record a visual review note.
To mark a field absent, check all relevant pages and state what you checked.
Exports contain only explicit reviews; unreviewed fields are listed separately.
Reviewer names are self-entered audit labels, not authenticated identities.

Original page previews require Poppler's `pdftoppm` on PATH. It is available in
the tested desktop runtime. Without it, use **Open PDF** or extracted text.
The interface uses local assets and requires no frontend build or CDN.

For isolated interface testing, use a different data directory and port:

```powershell
python -m skony serve --port 8766 --data-dir output/workbench-qa
```

Engineering test decisions in that directory must not be treated as gold labels.
The Docker runner is now packaged but still needs a Docker-enabled build/run
check. This is the local live-development workflow. To use the public practice
document without a key, run `python -m skony serve --mode replay`; this defaults
to the separate `output/workbench-replay/` store and blocks live extraction.

Copy `.env.example` to `.env` and put the hackathon access email's exact values
in `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`. The URL should be the API base,
usually ending in `/v1`, not the full `/chat/completions` URL. The file is ignored
by Git. The CLI loads this file without printing secrets. Existing environment
variables take precedence. If using an alias, record the provider's mapping to
Apertus 1.5 in the final report; a successful API prompt alone does not prove identity.

```powershell
python -m skony smoke
python -m skony ingest data/private/example.pdf --output output/document.json
python -m skony extract data/private/example.pdf --output output/extraction.json
```

For an offline engineering fixture, both inputs must be explicitly labelled
synthetic. It is not a real-model benchmark:

```powershell
python -m skony verify output/document.json output/candidate.json --output output/located.json
```

To reproduce the evidence checks on the recorded real-model pilot without
another API call:

```powershell
python scripts/replay_pilot.py
```

This requires the locally retained pilot files under `output/live_pilot/` and is
clearly labelled as a recorded-output replay. The data have not been packaged
for public distribution yet. API calls use constrained JSON output; a provider
that does not support it must be checked explicitly rather than silently bypassed.

Each output includes original page text and source offsets. Review source wording
and semantic assignment before relying on or exporting an extracted result.
Scanned PDFs without text and documents above the explicit input limit stop for
review; the current implementation does not run OCR or silently truncate them.
An existing OCR layer may contain corrupt text. A matching string alone does not
establish that the OCR is faithful to the visual page. Line-break-only differences
can be mapped back to original spans; words and punctuation are not fuzzy-matched.

The `make run` Docker entry point is now present. These local CLI checks do not
replace the pending container build/run/rebuild verification; see [RUNNING](RUNNING.md).

