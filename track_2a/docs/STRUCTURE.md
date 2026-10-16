# Structural content inventory (`skony.structure-inventory.v0.1`)

The pipeline's core eight fields are text claims with page/span provenance.
Parliamentary PDFs also carry **structural content** — annexes, embedded
raster images, and table regions (budgets, staffing plans). This layer makes
that content **visible, counted, located and queryable** without interpreting
it: *inventory, not interpretation*.

## Why inventory, not interpretation

1. **Provenance discipline is the product.** A cell value reconstructed from
   layout geometry is not a verbatim quote of the page text stream; attaching
   it as if it were would silently weaken the trust model every other field
   follows. Structural items therefore record *that something is there and
   where*, and leave value-level extraction to a reviewer or a future,
   explicitly-labelled capability.
2. **No silent OCR.** `pdf.py` deliberately refuses to OCR textless pages.
   The inventory keeps that promise: scans are *recorded* as
   textless-plus-image, which makes the gap queryable instead of invisible.
3. **Determinism.** Detection is regex/heuristic-only, versioned by method
   labels (`line-anchored-marker-v1`, `pypdf-xobject-v1`,
   `text-grid-heuristic-v1`), runs keyless, and produces byte-identical output
   on re-runs. It never enters the cached extraction payload, so response
   replay identity is unaffected.

## What is detected (and how)

| Item | Method | Covers | Does NOT cover |
|---|---|---|---|
| `annexes[]` | line-anchored printed markers (Annexe/Beilage/Anhang/Allegato/Annex + number/label), page + char offsets | Marked annex headings in DE/FR/IT/EN | Unmarked attachments; annex *content* |
| `images[]` | `/XObject` raster resources per page, name + pixel size | Embedded photos/scans/logos | Inline `BI/EI` images, SMasks, vector graphics; image *content* |
| `table_hints[]` | ≥3 consecutive column-gap/digit-dense lines (plus CHF/Total/Budget keywords), page + char span | Ruled and grid-like budget tables in text-born PDFs | Borderless layout tables; cell structure; multi-page stitching |
| `textless_pages` | from intake | Scan detection (needs-OCR stratum) | OCR itself — by design |

Every inventory object ends with an explicit `limitations` array so downstream
consumers cannot mistake detection for completeness.

## Corpus census (evidence)

`scripts/structure_inventory.py` runs the inventory over the full fetched
corpus and aggregates by body and language. Current private-corpus results
(44 PDFs, 153 pages, DE+FR, municipal + cantonal, one preserved failed fetch
kept in the denominator):

| Stratum | Documents | Notes |
|---|---|---|
| with annex markers | 5/44 | Bern 2, Waadt 1, Zürich 2 |
| with embedded images | 22/44 | 116 images total; all 8 Nidau docs image-bearing |
| with table regions | 1/44 | one 29-page Bern budget/financial report, 44 regions |
| with textless pages | 4/44 | Zürich 3, Nidau 1 — the scan stratum needing OCR |
| parse failures | 0 | one failed *fetch* preserved, not a parse failure |

Two findings fall out directly: **(a)** structural content is concentrated —
budget tables appear in financial reports, not in Vorstoss requests, which
justifies treating tables as a per-document-type capability rather than a
global one; **(b)** the scan stratum (9% of documents) is exactly where
extraction abstentions cluster, which the gold-set evaluation reports
separately instead of filtering out of the denominator.

## Relation to Docling

Docling is the designated successor for value-level structure: its document
JSON carries table cells and figures with bounding-box provenance, which is
the same trust shape as this inventory (and the v0.2 `PDFRegion` contract is
already coordinate-transform-validated for that carrier). It is not bundled
here because its dependency footprint (torch/transformers) conflicts with the
self-hostable 3-dependency deployment target; the inventory layer defines the
contract Docling output will satisfy.
