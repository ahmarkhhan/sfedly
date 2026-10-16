# Public repository, data and credentials

Updated 16 October 2026. The public checkout is `sfedly/` in the development
workspace and publishes to <https://github.com/ahmarkhhan/sfedly>. Run Git and
release commands inside that checkout. The surrounding workspace also contains
private research state and unrelated projects; it is not a publication source.

## What is synchronized

The repository includes the active converter, explorer, evidence viewer,
vocabularies, evaluation tools, engineering tests, technical requirements in
the root `docs/`, and public synthetic fixtures in `track_2a/data/sample/`.
The report source and PDF are maintained together. Existing remote report,
results and CI updates are retained when merging local implementation changes.

The synchronized implementation passes **245 Python engineering tests and 16
interface-controller tests** on 16 October 2026. The isolated public-source
startup check passes PDF preview, review persistence and replay isolation.
Docker execution and real-corpus semantic accuracy remain unverified here.

## Data boundary

| Data | Published | Purpose |
|---|---|---|
| `data/sample/` including `contracts-v0.2/` | Yes | Authored synthetic practice and contract checks; not model output or gold |
| `docs/evaluation-v1/` | Yes | Evaluation protocols, templates and schemas; not completed human annotation |
| `data/private/` | No | Local source PDFs, metadata and corpus manifests; redistribution rights unverified |
| `output/` and `tmp/` | No | Model responses, request cache, SQLite reviews, audit state and execution logs |

The local corpus accounting records 45 source rows, 44 hash-pinned PDFs and
one failed source. Language metadata hints are 24 DE, 8 FR and 13 unknown;
these are not human-verified coverage. Private data are intentionally absent
from the public checkout. Public replay uses the synthetic fixture; repeating
the private DE/FR experiment needs the separately retained inputs and cache.
No measured gold accuracy is claimed.

## Secrets and release checks

Keep live endpoint credentials in ignored `track_2a/.env` or environment
variables. Only `.env.example` with empty/example values is public. Never
publish private PDFs, review stores, response caches, request headers or local
logs. The Docker context allowlist includes only runtime source and public data.

From the repository root, stage the intended public files and run:

```powershell
python track_2a/scripts/check_publication.py
# Optional: also compare known local key values without printing them.
python track_2a/scripts/check_publication.py --env-file ../track_2a/.env
```

The check inspects indexed bytes and reachable Git history for recognizable
credential formats and known values, and rejects private/runtime paths in the
publication set. It prints file names and object IDs only. Pattern matching
cannot guarantee the absence of every possible secret; review the staged file
list before pushing. A disclosed credential must be revoked at its provider;
deleting a file alone does not remove it from Git history.

## Reproduce checks

From `track_2a/`, install `requirements.txt` with Python 3.11+, then run:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests
node --test tests/evidence-ui.test.cjs tests/explorer-ui.test.cjs tests/scoped-ui.test.cjs
python scripts/check_clean_start.py
```

The preview check needs Poppler. Rebuild the report with the separate
`requirements-report.txt` dependency and `python scripts/build_report.py --check`.
PyMuPDF is an AGPL-3.0/commercial dependency; the project's Apache-2.0 source
licence does not replace dependency licensing obligations.
