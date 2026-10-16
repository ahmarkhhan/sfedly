# First live CSCS / Apertus pilot — 14 October 2026

**Outcome:** CSCS authentication works. A real Apertus 1.5 70B response can be
converted into four source-located raw fields on one parliamentary PDF, while
withholding unreliable/missing fields. This is an engineering pilot, not a
dataset-level accuracy result or a human-reviewed gold-set evaluation.

## Connection and model identity

The user supplied `https://api.inference.cscs.ch/v1` from the hackathon access
email. The [CSCS documentation](https://docs.cscs.ch/services/inference/api/)
confirms this base URL, bearer-key authentication and the model-list/chat endpoints.
The authenticated `/models` request returned HTTP 200 and the official 8B/70B
Apertus 1.5 models. A short 8B connectivity prompt passed. The client now rejects
responses that report a different model identity.

Credentials are read from the ignored local `.env`; no keys are stored in the
pilot reports, prompts or output records. Ignore patterns also cover copied
files ending in `.env`. The tested 70B model is now the local default.

## The real source

The input is a two-page Nidau postulate about a synthetic ice rink on the library
square, sourced through OpenParlData's documented archive URL from its Nidau
metadata export. The second page is a product brochure annex. Both pages were
rendered and visually inspected by the assistant.

The retrieved PDF's existing OCR layer preserves most typed text on page 1 but
garbles the submitter and much of the annex. Its printed name is readable in the
page image, illustrating why a text match cannot establish faithful OCR.

The source manifest records the original municipal URL, retrieved archive URL,
metadata identifiers, retrieval time and the actual PDF byte digest. The export's
`hash` field differs from the retrieved-byte SHA-256; its meaning/currentness has
not been established. Both are retained without treating them as interchangeable.
The PDF remains in the ignored local pilot directory pending redistribution checks.

## Observed calls

| Model and prompt | Tokens | Model-call time | Result |
|---|---:|---:|---|
| 8B, raw-v0.1 | 1,800 | 3.047 s | Returned malformed schema-like text; rejected |
| 8B, raw-v0.2 | 1,548 | 2.297 s | JSON syntax valid, but null values had non-null evidence; rejected |
| 70B, raw-v0.2 | 1,725 | 7.234 s | Passed schema validation; retained for evidence checks |

`raw-v0.2` uses provider-constrained JSON generation and an explicit output shape.
This follows the [vLLM structured-output API](https://docs.vllm.ai/en/latest/features/structured_outputs/),
and was accepted by the real CSCS endpoint. Unsupported response modes are not
silently downgraded. Raw responses and run metadata were preserved, including failures.

## Evidence results from the frozen 70B response

| Field | Result with evidence-v0.2 | Qualification |
|---|---|---|
| Title | Source located, exact | Still requires semantic review |
| Raw affair type | Source located, exact | Source term preserved |
| Printed date in submitted-date field | Source located, exact | Date presence does not by itself establish the procedural event |
| Question/request | Source located, whitespace-only mapping | Original line breaks restored in the output and source offsets |
| Submitter | Abstained: OCR noise | Corrupt OCR was not exported as a person's name |
| Government answer | Model abstained | Not present in these two pages |
| Decision | Model abstained | Not present in these two pages |
| Decision date | Model abstained | Not present in these two pages |

The original verifier rejected the question because the model collapsed PDF
line breaks. The revised verifier permits only whitespace variation and maps the
match back to unchanged page text. It does not change words/punctuation or search
other pages to hide an incorrect page claim. Ambiguous matches still abstain.
Every located result remains `needs_human_review`; no field is automatically
declared semantically correct.

This replay used the saved real-model output with **zero new inference calls**.
The preserved raw response remains unchanged. One PDF does not establish that
70B generally outperforms 8B, that the system is ready for unattended operation,
or that a particular per-document cost has been achieved.

## Reproduce and continue

From `track_2a/`:

```powershell
python scripts/replay_pilot.py
python -m unittest discover -s tests -v
```

The replay requires the retained local `output/live_pilot/nidau-70b-v02/` inputs.
The revised pipeline passes **21 engineering tests**. It uses one strict schema,
preserves original source text, records model/token/latency metadata and rejects
invalid model results.

Next: build the review interface, gather a small German/French sample across
multiple bodies, obtain human-reviewed annotations, measure semantic errors and
schema coverage, and add the judge-facing Docker entry point.
