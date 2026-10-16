# Gold annotation guide

For the independently reviewed v0.2 study, follow the
[evaluation implementation guide](EVALUATION_IMPLEMENTATION.md). It adds blind
packets, explicit original annotation provenance, competence/calibration and
independence checks, fixed relation universes and frozen-cohort scoring. The
workbench-confirmation/export workflow below remains the legacy review workflow;
model-assisted confirmations do not become blind gold automatically.

How to produce the human-reviewed gold set that the evaluation is scored
against. The original PDF is always authoritative; you are recording what a
human verified against it, not what the model guessed.

## What you are deciding

For each of the eight extraction fields, make a decision only when you can
verify it. A document qualifies for the complete gold set when all eight
fields have justified decisions. Leave uncertain fields unreviewed; record
the limitation and arrange review by someone who can read the source.

| Field | What to verify |
|---|---|
| `title` | The affair's title as printed. |
| `affair_type_raw` | The request type exactly as written (Motion, Postulat, Interpellation, Anfrage, Initiative…). Keep the raw wording. |
| `submitter_raw` | Who submitted it, as written. If OCR corrupts the names, inspect the original page. Leave unreadable names unreviewed. |
| `submitted_date_raw` | The submission date as printed. Note: a document may print several dates; capture the *submission* one. |
| `question_text` | The actual question/demand (Antrag / demande). |
| `answer_text` | The government's answer, if this document contains one. Often absent in a request-only document. |
| `decision_raw` | The decision/outcome wording, if present. |
| `decision_date_raw` | The decision date, if present. |

## The three decisions

- **Confirm** — the model's located passage is correct. Use it when the
  highlighted source span says exactly the right value.
- **Correct** — the value is present but the model got it wrong or located the
  wrong span. Supply the value, the page, and the supporting passage. If you
  read it from the page image (scanned/no text layer), say where you looked in
  the note; do not invent text offsets.
- **Absent (missing)** — you checked the relevant source scope and determined
  that the field is absent. Write which pages and scope you checked. An
  unreadable page, weak OCR, or uncertain language is not evidence of absence.

If the value might be present but you cannot read or interpret it, leave the
field unreviewed. Use **Undo** if it was already marked absent by mistake.

## Rules that protect the evaluation

1. **Faithful wording.** Copy the source's words, punctuation and language.
   Do not translate, normalise or "improve" the value. Derived/normalised
   forms are a separate layer and are not your job here.
2. **No invention.** If it is not in the document, it is absent. A plausible
   value you cannot point to on a page is a hallucination and will corrupt the
   scorer.
3. **Request vs response documents.** Many request PDFs contain no answer or
   decision — marking those `answer_text`/`decision_*` absent is correct, not
   a failure. The response document (where present) carries them.
4. **One affair per document.** If a PDF bundles several affairs (common in
   council-meeting objects), annotate the one named in the document's title /
   source metadata only when that target is unambiguous. Otherwise leave it
   out of this single-affair evaluation and disclose the exclusion.
5. **Sign your work.** Use a consistent reviewer name. Automated interface
   checks are labelled "Automated UI QA" and are excluded from gold
   automatically — do not use that label for real reviews.

## Reviewer-competence disclosure

If a document is in a language you cannot read confidently, leave uncertain
fields unreviewed and request a competent reviewer. Translation assistance
does not establish that a field is absent. Disclose actual reviewer language
competence and any assistance in `--reviewer-note`. An abstention is an
unreviewed field, not an absent gold label.

## Workflow

1. Start the workbench in live mode with the fetched corpus loaded.
2. Import saved batch results using `load_corpus_into_workbench.py --batch-run`
   (see `BATCH_EVALUATION.md`), or run extraction for an individual document.
   Inspect the original PDF while reviewing each field.
3. When a document's eight fields are all decided, it is gold-eligible.
4. Export the set:

```bash
python scripts/export_gold.py --store output/workbench --out data/gold/review-20261015 \
  --reviewer-note "State actual reviewer language competence and assistance here."
```

Choose a new, empty export directory each time. The exporter excludes
incomplete documents, automated-QA entries and synthetic practice examples.
The manifest lists exactly which records belong to this export and their
checksums. Export eligibility records explicit decisions; it does not certify
reviewer competence or source redistribution rights. Keep source material
private until its rights are verified.

## Target (and honest fallback)

Target: 12–16 documents, German + French, at least 3 bodies, at least 2
government levels, at least 3 scanned/OCR-poor, and affairs that pair a
request with a government response where available. If time runs short, ship
fewer fully-reviewed documents over more half-reviewed ones — the scorer only
consumes complete gold, and the report must state the actual counts and any
language/body shortfall.
