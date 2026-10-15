# Batch extraction and response replay

Run these commands from `track_2a/` with Python 3.11+ and `requirements.txt`
installed. This pipeline freezes model responses and prepares suggestions for
human review. A replay or a source-located field is not a gold label or a
measurement of extraction accuracy.

## Run a bounded batch

The existing selector/fetcher produce `data/private/gold/fetch_manifest.json`.
The local manifest currently has 45 entries: 44 downloaded PDFs and one failed
download. The runner keeps failed downloads in its denominator. Every usable
PDF needs its pinned SHA-256 and a relative path within that corpus directory.

Configure the existing `.env` with `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`.
Live execution transmits extracted PDF text to that endpoint. Use an output
directory that does not already contain a run:

```powershell
python scripts/batch_extract.py --mode live --limit 2 --out output/batch/first
```

Remove `--limit` only when ready to process every manifest entry. `--limit`
selects the first N entries, including failed downloads; it never changes the
source manifest. Live mode requires an explicitly identified Apertus 1.5
model. The default generation limit is 4,096 tokens, temperature zero.

The runner saves `run_ledger.json` before work and after every item. Each row
records intake/cache/endpoint/schema/filesystem failures or its result path,
request and response digests, token usage and original model latency. A
schema-invalid completed response stays cached and fails again on replay.
HTTP/connection failures are recorded but are not successful response-cache
entries; a later explicit live run can retry them. There are no automatic
retries or alternate models.

Exit codes: **0** = nonempty run, every selected row succeeded; **1** = one or
more selected rows failed (or no rows); **2** = preflight/configuration failure.
A completed ledger may therefore contain failed rows. Always inspect counts.
Stop/interruption leaves a checkpoint; resume the same configuration with:

```powershell
python scripts/batch_extract.py --mode live --limit 2 --out output/batch/first --resume
```

Resume archives the preceding ledger and rebuilds an attempt using existing
cached responses. It does not erase earlier result files. Input manifest,
prompt, model, generation settings, parser or verifier changes require a new
output directory. Use one sequential writer per cache/run directory.

## Replay with no API credential

```powershell
python scripts/batch_extract.py --mode replay --limit 2 --out output/batch/replay
```

Replay skips `.env`, supplies no API credential and cannot call the model.
Specify `--model`, `--base-url` and `--model-revision` to match any nondefault
recorded run. `--max-tokens`, prompt, schema and text must also match. A missing
or corrupt cache entry becomes an explicit failed item; there is no fallback
to a live call. A changed verifier rebuilds source checks from the same raw
response without regenerating it. The recorded generating prompt version stays
attached to that response.

The cache key covers the exact effective messages, schema, model, endpoint,
generation settings, optional model revision, PDF/page-text digests and parser
version/policy. API credentials and verifier version do not affect generation
identity. Each entry also carries content and whole-record checksums, original
completion time, usage and latency. Checksums detect inconsistent files; they
are not signatures that authenticate a writer. Provider aliases without a
known immutable revision remain a reproducibility limitation.

The `skony.cache.v0.2` format does not silently reuse old weaker cache entries.
Keep legacy files as evidence; do not rename them into the new cache.

Token totals in a replay ledger describe the **original inference**. They are
not newly billed tokens. `usage_reporting` identifies which items/provider
fields reported usage; missing values are unknown. `processing_seconds` is
this run's work, while `model_latency_seconds` is the recorded original call.
No currency cost is inferred.

## Load saved suggestions for review

```powershell
python scripts/load_corpus_into_workbench.py --store output/workbench --batch-run output/batch/first
$env:PYTHONPATH = 'src'
python -m skony serve --mode live --data-dir output/workbench
```

Use matching `--fetch-dir` and `--cache-dir` if you changed their defaults.
Import checks manifest/PDF/result/cache digests and recomputes the source
verification before accepting suggestions. Reimporting the same result adds
no duplicate run or revision; existing human decisions remain intact. A
currently running extraction cannot be replaced by an import. The importer
never calls a model. The individual workbench **Extract** action remains an
explicit live call; use batch import to reuse these results.

Document roles selected from categories/filenames are marked as unverified
hints until a reviewer checks them. Missing licence/role provenance is
backfilled without replacing existing labels. Preserve unknown language and
level metadata; do not infer evaluation breadth from a selection target.

Follow [the annotation guide](ANNOTATION_GUIDE.md). Uncertain or unreadable
fields stay unreviewed; they are not absent labels. Export to a new directory:

```powershell
python scripts/export_gold.py --store output/workbench --out data/gold/review-20261015
```

Only complete explicit decisions can export. Synthetic/practice and automated
QA documents are excluded. The export manifest lists records and checksums;
source rights/provenance remain attached. This eligibility check does not
certify reviewer competence or dataset redistribution rights.

## Bounded real-data proof

```powershell
python scripts/check_batch_replay.py --live --out output/pipeline-proof
```

This explicitly allows at most two uncached calls: one supported, hash-verified
DE PDF and one FR PDF. It also preserves an existing failed-fetch row. The
second run has an empty API key and an HTTP transport that fails if contacted.
`proof.json` records whether results match, the manifest is unchanged, failures
are retained and replay made zero calls. Its inputs/cache/results remain in
ignored private output. It creates no human annotations and is not a
representative quality benchmark. See [verification status](PIPELINE_VERIFICATION.md)
for what actually ran here.

Raw caches contain source text and model responses. Keep them private with the
source PDFs until item-level publication rights and redactions are settled.
