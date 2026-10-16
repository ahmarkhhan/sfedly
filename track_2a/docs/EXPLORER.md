# Affairs explorer

Open `/explore` on the running Skony server. The review screens link to it.
With the normal local development port, the address is
[http://127.0.0.1:8765/explore](http://127.0.0.1:8765/explore).
Restart a running server after updating the Python sources; Docker users rebuild
using the existing running guide. No dependencies or database migration are added.

## What someone can do

1. Search original PDF text, names, filenames and source affair IDs. Search folds
   case and accents and requires all query fragments. It can find documents before
   extraction or human review. Scanned pages without a text layer remain visible,
   but require OCR or visual reading before text search can find their contents.
2. Filter by parliament, language, topic keyword hint, located request/answer/
   decision evidence, extraction availability, and real versus practice sources.
   Topic hints use a small DE/FR/IT/EN word-prefix list. This is discovery support,
   not semantic translation or an official subject classification.
3. Use the three evidence-question shortcuts to find requests, government answers
   or decisions already located in the selected fields. The cards show exact text,
   field coverage and a link to the source, rather than generated factual answers.
4. Open a dossier. Read request/answer/decision fields per PDF, follow dated events,
   inspect submitter/signatory blocks, and read original source text with highlights.
   Every located value links to its page and directly to the existing review screen.
5. Export all matching dossiers as a JSON research brief or field-per-row CSV.
   Exports include document hash/revision, exact passages, source links, reviewer
   identity where available, synthetic labels and explicit field status. Pagination
   affects the screen only. CSV protects formula-like source strings with a leading
   apostrophe and quotes multiline content. Relative PDF links resolve against the
   local Skony server; publisher links remain usable outside it where available.

Filters and an open dossier have shareable local URLs. The document-reviewed
toggle suppresses model field proposals while keeping original source text searchable.

## Evidence rules

- Dossiers join only identical provider/body/affair source identifiers. Missing
  identities stay document-specific. Bodies remain distinct even if named alike;
  practice sources never join real affairs. Associations are explicitly labelled
  unverified source metadata. This projection does not establish affair membership.
- Each PDF keeps its own fields. No Q/A pairing across PDFs or within multi-affair
  minutes is inferred. Scoped review at `/scoped` remains the place to establish
  those boundaries and produce dependency-checked accepted snapshots.
- Field values distinguish `document_reviewed`, `source_located_unreviewed`,
  `withheld_unreviewed` (hidden by field mode), and `not_located`. An explicit document-level reviewer absence is retained. These
  are v0.1 document decisions, not v0.2 scoped eligibility or gold certification.
- Counts describe text located in the current local sample. “No answer text
  located” does not establish that a government never answered. No official
  procedural status, overdue flag or response-time statistic is invented.
- Timeline dates keep independent citations and review labels. Only numeric ISO
  dates and `day.month.year` dates are sorted. Other wording and missing dates are
  placed in an explicitly undated/unsortable group. No date is borrowed from
  retrieval metadata; answers stay undated because the current schema lacks an
  answer-date field.
- Signatories stay in the original text block. There is no inferred actor identity,
  party affiliation, co-signatory split or unsupported additional role.
- The explorer reads one SQLite snapshot for every projection and performs no
  mutations, model calls, scoped migrations or annotation. Research JSON uses
  `skony.research-brief.v1`, separate from reviewed and gold export contracts.

## Local API

| Route | Purpose |
| --- | --- |
| `GET /api/explorer` | Paginated dossier summaries, source snippets, facets and coverage |
| `GET /api/explorer/dossiers/{id}` | Document fields, original page text, actors and dated events |
| `GET /api/explorer/export?format=json` | All filtered dossiers with evidence and limitations |
| `GET /api/explorer/export?format=csv` | All filtered document fields in spreadsheet-ready rows |

Search/export filters: `q` (maximum 250 characters), `body` (the opaque facet key),
`language`, `topic`, `evidence`, `sources` (`all`, `real`, `practice`),
`reviewed_only` (`true`, `false`). Search also accepts `offset` and `limit`
(1–100; default 30). Detail accepts only `reviewed_only`. Duplicate and unknown
filters are rejected. Existing host/origin policy and static-file allowlist apply.
Publisher URLs permit HTTP(S) only and reject embedded credentials.

## Verification and limits

On 16 October, 235 Python engineering tests and 9 offline controller tests passed.
Ten new Python tests cover unextracted multilingual discovery, exact Unicode
source offsets, conservative group identity, absent/undone reviews, independent
date evidence, complete research exports, CSV injection protection, safe links,
facet identity, input validation, read-only behavior and local HTTP routes. Five
new controller tests cover stale search/detail/source responses, failure cleanup,
export filters and Unicode versus visual evidence. These fixtures are synthetic
engineering checks, not accuracy or gold annotations. The initial sandboxed suite
could not use Windows loopback/atomic-file operations; the full suite passed when
run with those operations available.

Browser QA uses the existing local collection through a read-only store. This
prototype scans the local SQLite collection per query; it is not a 300,000-document
search service. No OCR, vector search, free-form answer generation, new live-model
extraction or external corpus synchronization is added. Real corpus quality,
coverage and pending evaluation gates remain as documented in BUILD_STATUS.md.
