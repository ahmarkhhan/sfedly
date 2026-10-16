# Skony event compliance review — 15 October 2026

> Current design and release authority: [project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md). This earlier review is retained
> as research history.

> Update after reading the supplied 8 October Q&A: the provider encourages a
> bounded request/answer subset, and does not mandate RDF/XML. The broader schema
> omissions below are scope and evidence gaps, not automatic disqualification.
> See the [complete assessment](15-hack-apertus-complete-assessment.md) for the
> revised priorities, source archive and challenge-specific distinctions.

## Verdict

**Partially aligned with online Track 2A / OpenParlData; not yet submission-ready.**

The project has a working Apertus extraction slice and a useful source-backed
review workbench. The remaining work includes mandatory submission packaging and
the evidence needed to answer the challenge's main research question. Improving
the interface alone will not close these gaps.

This review covers the files in `D:\development\Skony`, the app running at
`http://127.0.0.1:8765/`, the existing tests, and current official event pages.
It assesses the online event, not the separate Liebefeld event. No application
code or human review decisions were changed, no new model inference was run,
and no event submission was sent.

## Official requirements checked

- [Online event](https://hackapertus.devpost.com/): deadline **16 October 2026,
  12:00 CEST / 15:00 Asia/Karachi**; submissions go through the organiser's site.
- [Project template](https://github.com/HackApertus/project-template): preserve
  `track_2a/`, which is the selected project root; provide a working Docker-based
  `make run` on a clean checkout, technical report, code, and required `LLM_*`
  configuration; `data/` must not exceed 100 MB.
- [Track 2A rules](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md):
  build with Apertus; disclose any supporting open-weight models; follow the
  chosen challenge's deliverables and judging criteria.
- [OpenParlData brief](https://hackapertus.notion.site/track-2a-openparldata):
  versioned documented representation with controlled vocabularies; Apertus
  PDF converter with page/span provenance; multilingual, multi-level evaluation
  against manually checked gold data; demonstrate at least one cross-parliamentary
  question. Judging focuses on **insight** and **breadth/applicability**. A
  well-supported partial or negative finding can succeed.
- [Submission form](https://hackapertus.ch/online-hack/submissions), inspected
  with **Track 2A - OpenParlData** selected: a **technical report PDF, maximum
  six pages**, and **GitHub repository URL** containing the converter, prompts,
  validator, and README with samples. Participant/team/model fields are also
  required. A demo video is not listed as a required OpenParlData form field.
- [Terms, section 6](https://hackapertus.ch/terms-and-conditions): code under
  Apache-2.0, non-code outputs under CC-BY-4.0, submitted datasets under
  CDLA-Permissive-2.0, with compatible third-party rights and item-level licences.

The challenge, selected submission form and terms were read in the rendered
browser because the web text extractor could not retrieve their full contents.
Do not replace this challenge's criteria with Track 2B's five-part rubric.

## Compliance matrix

| Requirement | Assessment | Evidence / remaining action |
|---|---|---|
| Correct challenge and folder | Pass | Active implementation is under `track_2a/`, labelled OpenParlData online Track 2A. |
| Built with Apertus | Implemented; live pilot recorded | Client uses required configuration; retained run identifies `swiss-ai/Apertus-v1.5-70B`. UI explicitly labels its initial result as recorded extraction. No fresh endpoint call was made in this review. |
| Converter, prompt and validator | Implemented first slice | Python PDF intake, structured prompt, strict Pydantic validation and deterministic quote verification. |
| Source traceability and abstention | Pass for implemented scope | Page, document hash, quote and original-text offsets; ambiguous or unsupported values withheld. Visual corrections are separately labelled and do not claim text offsets. Semantic correctness still needs human checking. |
| Human review | Implemented | Confirm/correct/absence/undo, persistent decisions, revision conflicts, audit history and reviewed-only export. Existing tests cover these operations. |
| Common affair representation | Partial | `skony.raw.v0.1` supplies eight raw fields. Controlled vocabularies, actor lists/roles, procedural history, related-affair links, structured table/image/annex representation and multi-page field assembly are not implemented. Standards mappings are an ideal in the brief, not a reason to claim absent integrations as delivered. |
| Multilingual, multi-level gold-set evaluation | Missing | One German, two-page Nidau municipal PDF is the retained live pilot. No reviewed cross-body corpus, scoring runner or dataset-level quality results were found. Synthetic French test text is not multilingual model evaluation. |
| Cross-parliamentary question | Missing | No demonstrated query across affairs from different parliaments. A chatbot is not necessary; a reproducible comparison with cited records could satisfy this part. |
| Evidence-based feasibility conclusion | Missing | Technical report describes planned evaluation, not measured generalisation or documented differences between bodies. |
| Clean-checkout Docker `make run` | Missing; submission blocker | No Makefile, Dockerfile or Compose configuration found. Current development instructions require local Python and Poppler. Server binds to `127.0.0.1`; container networking must be addressed and tested when adding Docker. Docker and make were not available on PATH during this review. |
| Technical report PDF, at most six pages | Missing; submission blocker | `track_2a/technical_report.md` is a candid draft, but no final report PDF exists in the reviewed project. |
| Public implementation repository and samples | Not established; submission blocker | This workspace is not a Git checkout, and no submission repository URL was established. Pilot PDFs/results are in ignored private/output directories; a clean checkout would not contain the current recorded demo. Package publishable samples or a reproducible retrieval workflow and example outputs. |
| Data size limit | Pass locally | `track_2a/data/` contains 7,539,852 bytes, about 7.19 MiB, below 100 MB. Recheck the actual published sample package. |
| Licensing | Partial | Apache-2.0 file exists. Draft mentions CC-BY-4.0, but final documentation/dataset licensing and third-party attribution need explicit packaging. Pilot manifest says redistribution licence is not yet verified. Resolve it before publishing source material. |
| Required model environment variables | Pass in implementation | `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`; configuration stays on the server. Runtime/API requirements in the copied track README still need concrete project instructions. |

## Checks performed

All **35 existing automated tests passed** on Python 3.11. The initial restricted
run passed 32 and could not connect for three local-server tests; rerunning the
same suite with loopback access passed all 35. These are engineering checks,
not extraction-accuracy measurements.

The running app showed one document and **0/8 fields reviewed**. Original PDF
page rendering and highlighted source evidence worked. The correction dialog
exposed source page, text/image basis, passage and review note. It was cancelled
without saving. Export was disabled while all fields were unreviewed.

The recorded 70B result and current verifier contain four source-located fields:
title, affair type, printed date and request. The corrupt submitter is withheld;
answer and decision fields remain null. The recorded call used **1,725 tokens**
and took **7.234 seconds**. These observations do not establish precision,
recall, field completeness or generalisation. In particular, four located fields
out of eight must not be advertised as 50% accuracy.

## Prioritized remaining work

1. **Make the project runnable by judges.** Add Docker and `track_2a/Makefile`,
   include Poppler, supply concrete environment instructions and public samples,
   and exercise `make run` from a clean copy without local private/output files.
   Never package the local `.env` files or API credentials.
2. **Produce challenge evidence.** Review a bounded set of real documents from
   multiple parliaments, languages and government levels. Include requests,
   executive answers and actual decisions, not only request documents. Preserve
   difficult/scanned examples and report failures. The brief sets no fixed
   minimum document count; a small defensible comparison is preferable to an
   unsupported broad claim.
3. **Complete or explicitly bound the representation.** Document field meanings,
   source versus normalized values, basic controlled vocabularies and the gaps
   found across bodies. Avoid silently collapsing multiple actors or multi-page
   answers into a single unsupported field. Explain what the prototype cannot
   represent and why.
4. **Show one cross-parliamentary answer.** Use the reviewed records to answer a
   concrete comparison question, with links back to original evidence and
   explicit limits on coverage.
5. **Finish submission artifacts.** Publish the implementation repository,
   README with real samples and licensing, and a report PDF of at most six pages
   explaining the schema, pipeline, measured evaluation, feasibility findings
   and limitations. Confirm the repository is accessible to judges.
6. **Remove conflicting submission material.** Root `technical_report.md`
   advertises unimplemented PostgreSQL/FastAPI components, `make eval` and
   placeholder metrics. `JUDGE_REPORT.md` concerns another event and contains
   obsolete statements. Exclude or clearly mark these historical documents so
   judges encounter the current, accurate report first.

There is no need to add more interface features to meet the next gate. The
priority is reproducibility, representative evidence and an honest completed
report before the deadline.
