# Gold annotation set

Exported: 2026-10-16T09:21:34Z  
Documents: 4  
Schema: `skony.gold.v0.1`

Each `*.json` file holds complete human review decisions for one source
document: every one of the eight extraction fields carries an explicit
confirm / correct / absent decision with provenance. Automated interface
QA entries and synthetic practice documents are excluded from gold.
Only files named in manifest.json belong to this export; their checksums are recorded there.

## Coverage

By language: de=1, fr=3
By body: Genève=2, Nidau=1, Waadt=1

## Reviewer-competence disclosure

Reviewers are team members (native-level DE and FR readers) following docs/ANNOTATION_GUIDE.md; each of the eight fields per document carries an explicit confirm/correct/absent decision against the source PDF. Single-annotation per document; no inter-annotator agreement was measured.

## Decision semantics

- `confirmed`: the located source passage was verified as the correct value.
- `corrected`: the reviewer supplied the value and the supporting passage.
- `absent`: a competent reviewer checked the relevant source scope and found the field absent.
- Unreadable or uncertain fields stay unreviewed and exclude the document from this complete gold set.

The original PDF remains authoritative; these decisions record what a human
verified against it.
