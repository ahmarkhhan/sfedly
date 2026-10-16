# Skony — parliamentary data with proof

> Planning history. The [15 October project direction](docs/16-project-direction.md)
> and [delivery backlog](docs/18-delivery-backlog.md) supersede conflicting scope,
> corpus counts and schedules below. See the [build status](track_2a/docs/BUILD_STATUS.md)
> for implemented capabilities.

**Recommended entry:** Hack Apertus online, Track 2A / OpenParlData.
**Submission deadline:** Friday 16 October 2026, 12:00 CEST / **15:00 Pakistan time**.
**Status:** idea selected; first extraction slice implemented; CSCS connection and
one real-document pilot completed. Dataset-level quality evaluation is pending.

## The pitch

Skony helps a clerk, journalist or researcher turn parliamentary documents into
comparable records while keeping the original evidence visible. Apertus 1.5
extracts what was requested, what the executive answered and what was actually
decided. Each field links to a source page and passage. Unsupported fields remain
empty, uncertain assignments go to review, and a comparison view works from
reviewed records. The contribution is a small reusable schema plus evidence of
which fields generalise across parliamentary bodies and which do not.

The demonstration should end with a useful comparison: **“How did the sampled
councils respond to requests about the same issue, and what evidence supports
each response?”** Choose the issue only after inspecting the available sample.
Do not promise a housing, transport or climate example before finding matching
source documents. Describe the sample's coverage; do not imply a nationwide result.

## Why this is the best fit for us

The [official Track 2A template](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md)
lists OpenParlData as a published challenge. Its
[challenge presentation](https://hackapertus-document-extraction-26a562.gitlab.io/)
asks for a common representation and an Apertus converter with an evaluation,
and prioritises insight and applicability. This aligns with the project already
outlined in this workspace, giving us a focused starting point.

OpenParlData already has an extraction/review workbench. A new interface alone
would be insufficient differentiation. Our proposed contribution is the tested
representation and a reproducible account of semantic failures, supported by a
compact interface that makes the evidence easy to inspect.

This is a recommendation based on published requirements, our current starting
point and time available. No winner probability or score has been measured.
The Devpost project gallery was unpublished when reviewed, so it does not support
claims about current competitors.

## Alternatives considered

| Direction | Attraction | Why it is a secondary choice for this deadline |
|---|---|---|
| UZH: cross-language semantic differences | Existing annotated SwissGov-RSD data; automatic scoring | Strong alternative if human annotation for Skony is unavailable; requires baseline reproduction and token-level Spearman scoring across EN–DE/FR/IT with the test split excluded from development |
| OST: inference over voting booklets | Human-annotated NLI benchmark with evidence | Requires German/French/Italian and cross-language pairs, a prediction CLI and macro-F1 evaluation; less reuse of our existing project work |
| FHGR: interview coach | Immediately understandable demo | Required consumer GPU deployment and fewer than five calls per answer add a separate feasibility gate, beyond interaction quality |
| ZHAW: robot grounding | A memorable multimodal demonstration; no robot required | The pipeline must run locally without external APIs; our available hackathon API does not by itself meet that requirement |
| Track 1B: Swiss Voices | Strong local relevance | The official template expects substantial curated evaluations; verified language/community annotations are a bottleneck for us |
| Track 1A: red-teaming | Valuable model research | Reproducible novel findings cannot be promised before experiments, and its publication rules differ |
| Track 2B: our own application | Flexible product scope | OpenParlData gives us a named user problem and explicit deliverables, so flexibility is less useful than focus here |

These are feasibility judgements, not predictions about other entrants. The
[published challenge descriptions](https://hackapertus.notion.site/track-2-apertus-adoption?pvs=25),
[SwissGov-RSD card](https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD) and
[official templates](https://github.com/HackApertus/project-template) are the
basis for the comparison. Challenge text was retrieved after the browser could
not render the guide reliably. One red-teaming child page remained incomplete;
its official GitHub README supplies that track's rules.

## Prototype scope

Aim for **three parliamentary bodies, German and French, and around 18 held-out
documents plus a small development sample**. This is a target pending corpus
inspection and available human review, not a minimum published by the challenge.
Prefer federal, cantonal and municipal coverage if comparable documents can be
obtained in time. Record sampling criteria before extraction.

The first version has eight raw fields: title, affair type, submitter, submission
date, question/request, executive answer, actual decision and decision date.
Retain source language and raw terminology. Add separately labelled normalised
types/outcomes only after checking their definitions and evidence. Represent
multiple questions, authors and answers as arrays in the next schema iteration;
do not flatten away differences to make comparison look successful.

The finished prototype should have:

1. **Source intake:** PDF identity, source URL, body/language metadata and page text.
2. **Apertus extraction:** versioned prompts, consistent JSON, explicit missing fields.
3. **Evidence checks:** deterministic quote-to-page/span resolution, with review reasons.
4. **Review interface:** original PDF/page beside fields; locate, accept or correct a field;
   preserve an audit record of corrections and the model's original suggestion.
5. **Comparison view:** filter reviewed records by issue/body and show requests,
   responses and decisions with original passages. Abstain where comparison is unsupported.
6. **Evaluation report:** measured field quality, source attribution, coverage,
   errors by body/language and where the schema cannot generalise.

## The demonstration

**Opening:** show two differently formatted documents from different bodies.
Explain the manual work needed to compare their content.

**Extraction:** run one document through the configured Apertus endpoint. Open a
field and locate its exact passage on the original page.

**Trust:** show a document missing an answer or containing a proposal that could
be confused with an actual decision. Skony leaves it unresolved or flags it for
review. Show a real observed error if available; label a seeded engineering
example explicitly if it is used.

**Value:** compare reviewed affairs addressing a shared issue. A source passage
supports each displayed result. Then show the measured evaluation and the
schema's documented limits.

For a demonstration fallback, preserve real recorded Apertus outputs with model,
prompt and input identifiers. Mark replay clearly. Synthetic fixtures and mocked
endpoint responses are engineering aids and must not be represented as inference.

## How we will measure it

Separate evidence location from semantic correctness. A perfectly copied date
can be a meeting date rather than the submission date; a quoted proposal can be
mistaken for the final decision. Neither is fixed by matching a string.

Use the same held-out sample and scorer for a simple rule baseline, raw Apertus
extraction and extraction with evidence checks. Report:

- Field precision/recall and accepted-field coverage, with explicit denominators.
- Correct page/span attribution, and the semantic correctness of located fields.
- Abstention reasons, incorrect rejection of valid evidence, and difficult scans.
- Correct question/answer/decision linkage, sliced by language and body.
- Latency and actual token usage; calculate money only from a documented tariff.
- Human review time if it can be measured with a real reviewer.

Human-reviewed gold annotations are needed before calling results ground truth.
Assistant-created provisional labels must be labelled as such until reviewed.
If language review is unavailable, report that limitation and reduce claims.
Small slices are indicative, not proof of readiness for all parliaments.

## Step-by-step build schedule

| Step | Work | Completion evidence |
|---|---|---|
| 1 — now | Rules review, scope, raw schema, PDF reader, API client, quote locator | Starter code and 21 passing engineering tests; dataset-level quality not measured |
| 2 — 14 October | Configure API; check served model; extract one real document; start the source manifest | CSCS access and one real-document pilot completed; broader sample selection remains |
| 3 — 14–15 October | Add schema arrays/vocabularies, review interface, persistent corrections | Reviewer can inspect and correct evidence on German and French examples |
| 4 — 15 October | Complete reviewed annotations, baseline comparison and cross-body question | Honest metrics, failure cases and one useful cited comparison |
| 5 — 15–16 October | Docker, public repository, technical report PDF and a short demo recording | Clean-checkout `make run`; submission fields complete |
| 6 — 16 October | Freeze features by 11:00 PKT; aim to submit by 13:00 PKT | Receipt before the hard 15:00 PKT deadline |

These are a proposed schedule, not saved reminders or an assurance about duration.
If time becomes tight, preserve working extraction, a defensible schema and
evaluation; cut decorative features and optional generated summaries first.

## Development and user responsibilities

I can implement and check the converter, evidence handling, review interface,
evaluation tooling, packaging and report in this workspace. We proceed one
working slice at a time, with each slice demonstrated before expanding scope.

You supply the hackathon endpoint configuration, confirm your registration/team
identity and help obtain or verify domain/language review. Your key belongs only
in `track_2a/.env`, which is ignored by Git. Publishing the repository and final
submission are separate actions to complete when the artefacts are ready.

## Submission and deployment

The active structure follows `track_2a/`, retaining the official README. The
[template](https://github.com/HackApertus/project-template) requires Docker launched
through `make run` and at most 100 MB in `data/`. The selected
[submission form](https://hackapertus.ch/online-hack/submissions) requires a
repository URL and a technical report PDF of at most six pages. Submit there,
not on Devpost. A video is useful for presentation but was not required by the
OpenParlData form when inspected.

Use the supplied API for development, and document a deployment path where the
same application calls a self-hosted or verified Swiss Apertus endpoint. Do not
claim air-gapped operation, a 20 GB inference footprint or a per-document price
without measuring the specific configuration. Apertus 1.5's official model card
currently points to patched serving frameworks; deployment compatibility must
be checked instead of assuming every generic runner supports it.

Code follows Apache-2.0 and documentation follows CC-BY-4.0 under the event
[terms](https://hackapertus.ch/terms-and-conditions). Public availability alone
does not give us a right to redistribute every source document. Keep a source
manifest and each item's licence; apply the event's dataset licence to our own
eligible contribution, while preserving third-party rights and attribution.

## Honest status

The current implementation handles PDF text, eight raw fields, a tested CSCS
client, evidence location and a local review workbench with persistent corrections
and reviewed-only exports. Corpus evaluation, a normalised schema, comparison
view and Docker runner remain to be built. See
[current build status](track_2a/docs/BUILD_STATUS.md). Nothing here guarantees a win;
the aim is a submission with a clear use case, working code and defensible evidence.
