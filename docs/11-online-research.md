# Hack Apertus website review — 14 October 2026

This review resolves the current task as the **online event**, following the
user's confirmation. It supersedes event-specific assumptions in the earlier
Liebefeld judge report and roadmap. Factual requirements, design choices and
unverified claims are kept distinct below.

## Verified requirements affecting our project

| Finding | Implication | Primary source |
|---|---|---|
| Online deadline: 16 October 2026, 12:00 CEST | 15:00 in Asia/Karachi; reserve time for submission | [Online event](https://hackapertus.devpost.com/) / [submission form](https://hackapertus.ch/online-hack/submissions) |
| Submission through the organiser's website | Devpost registration does not submit the project | [Track 2A README](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md) |
| OpenParlData is a Track 2A challenge | Use `track_2a/`; requirements and scoring differ from Track 2B | [Track 2A README](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md) |
| AI coding assistants allowed | Codex can implement the project | [FAQ, expanded online section](https://hackapertus.ch/faq#online-hackathon) |
| Track 2 solutions must use Apertus 1.5; supporting open-weight models allowed with disclosure | No unsupported “Apertus-only is mandatory” assertion | [FAQ](https://hackapertus.ch/faq#online-hackathon) |
| Community quantised builds allowed in Track 2; official checkpoint required for Track 1 | Treat Track 1/2 model rules separately | [FAQ](https://hackapertus.ch/faq#online-hackathon) |
| Track structure, Docker `make run`, technical report and data cap | Current CLI starter is not yet submission-ready | [Project template](https://github.com/HackApertus/project-template) |
| Selected OpenParlData form: report PDF ≤6 pages and converter/prompts/validator/samples repository URL | PDF remains outstanding; the form does not require a demo video | [Submission form](https://hackapertus.ch/online-hack/submissions), inspected after selecting OpenParlData |
| Track 2B has a separate five-dimension scoring rubric and mandatory deployment options | Do not substitute its rubric for OpenParlData's challenge criteria | [Track 2B README](https://github.com/HackApertus/project-template/blob/main/track_2b/README.md) |
| General event licensing specifies code, documentation and datasets separately | Retain third-party rights and item-level data licensing | [Terms §6](https://hackapertus.ch/terms-and-conditions) |

The programme page still says “Final submissions on Devpost”. This conflicts
with the selected submission form, guide and GitHub README. Use the explicit
submission instructions, which consistently direct us to the organiser's form.

## Why OpenParlData is the recommended direction

The [published presentation](https://hackapertus-document-extraction-26a562.gitlab.io/)
describes heterogeneous parliamentary PDFs and asks for a common schema,
Apertus conversion with provenance, and evidence on a multilingual sample.
Its main assessment is insight into schema feasibility and breadth/applicability;
a well-supported partial result can be valuable. OpenParlData already operates
a review workbench. The proposed differentiator is measured semantic extraction
and a documented reusable representation, not merely a replacement interface.

This is an inference about fit, not a score prediction or privileged jury advice.
The public Devpost gallery was unpublished. No competitor ranking or novelty
claim can be established from it.

## Data-source triage

These are reviewed landing pages/catalogues and relevant descriptions, not an
exhaustive review of all datasets or every downstream site they link to.

| Source | Possible use | Decision for the prototype |
|---|---|---|
| [OpenParlData](https://openparldata.ch/), [API](https://api.openparldata.ch/documentation), [exports](https://files.openparldata.ch/exports/) | Affairs metadata and linked documents | Primary source; select a bounded sample after checking licence and actual content |
| [SwissGov-RSD](https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD) | Human-annotated cross-language semantic differences | Strong alternative project, not parliamentary extraction ground truth |
| [I14Y](https://www.i14y.admin.ch/) | Government catalogues, concepts and public APIs | Possible later vocabulary/discovery reference; not a blanket data licence |
| [opendata.swiss](https://opendata.swiss/) | General Swiss government datasets | Possible enrichment; not needed for the extraction MVP |
| [SNSF](https://data.snf.ch/) | Research funding datasets | Could support a funding application, outside this scope |
| [Hugging Face datasets](https://huggingface.co/datasets) | Models, datasets and published artefacts | Useful distribution and discovery; licence checks are per dataset |
| [Kaggle](https://www.kaggle.com/datasets) | Broad dataset catalogue | No necessary role in this challenge |
| [SwissNLP / SwissCoco](https://swissnlp.org/swiss-corpora-collection/) | Text/speech corpus index with varied use restrictions | Relevant to Swiss Voices; not a single unrestricted dataset |
| [opensource.admin.ch](https://www.opensource.admin.ch/en/) | Federal software catalogue | Reference software resource, not a parliamentary dataset |
| [Open Source AI Definition](https://opensource.org/ai/open-source-ai-definition) | Meaning of open AI | Context for openness; do not equate public downloads with unrestricted rights |

The exports directory includes very large files, including multi-gigabyte vote
exports. Download only the needed body/document sample. A raw full-corpus mirror
would exceed the submission data budget and serve no prototype purpose.

## Review coverage

Main site pages were inspected using the rendered website because its raw HTML
is a client-rendered shell. The public FAQ answers were expanded, and the
OpenParlData submission selection was inspected without submitting anything.

| Group | Pages inspected |
|---|---|
| Core and participation | `/`, `/program`, `/forhackers`, `/online-hack`, `/getinvolved`, `/together`, `/open-data-sources`, `/apertus`, `/apertus/data`, `/faq` |
| Online resources | `/online-hack/submissions`, `/online-hack/cscs/getapi`, `/online-hack/phoeniqs/compute`, `/online-hack/hugging-face` |
| Regional/community events | `/regions/bern-liebefeld`, `/regions/zurich`, `/regions/basel`, `/regions/lausanne`, `/regions/stgallen-hack`, `/student-award`, `/program/midway-event` |
| People and involvement | `/voices`, `/about/team`, `/about/board`, `/contributor-wall`, `/mentors`, `/become-a-mentor`, `/volunteer`, `/calls`, `/communitypartner`, `/academia-partner`, `/data/data-provider` |
| Support and presentation | `/sdg`, `/mediakit`, `/medien`, `/deck`, `/deck-onsite`, `/deck-liebefeld`, `/academia-deck`, `/getbadge`, `/badge-partner`, `/partner-video` |
| Policy | `/imprint`, `/privacy-policy`, `/terms-and-conditions`, `/code-of-conduct` |
| Publicly reachable partner material | `/regions/zurich-hack`, `/regions/basel-hack`, `/partnerassets`; not used as participant challenge rules |
| Aliases | `/calls/partners` redirects to `/calls`; `/midway-event` redirects to `/program/midway-event` |
| Devpost | Overview, Resources, Rules, Project gallery, Updates and Discussions; authenticated “My projects” not accessed |
| Authoritative linked material | All four GitHub track READMEs; project template and licence; Apertus 1.5 8B/70B model cards; model docs; guide and submission instructions; OpenParlData presentation; listed data-source landing pages |
| Guide children | Registration, schedule, online sessions, communication, teaming, Track 1/2 overview, resources/tools, mentors, awards, submission and recordings/slides index; five Track 2A briefs, Track 2B and Swiss Voices; red-teaming child returned incomplete content, covered by its GitHub README |

`/onepager` redirects to a PDF that did not yield readable content through the
available web extraction. Some Notion pages initially returned unreadable content;
linked-page text retrieval recovered the five academia briefs. A few ancillary
pages and the red-teaming child remained partial. We used the official templates
for corroboration and preserved the guide/challenge retrieval indexes under
`docs/research`. Experimental routes, private
review/jury URLs, sign-in-only content, video recordings and every catalogue item
are not claimed as reviewed. Supporting deck text was inspected for project
relevance; stale deck details do not override current challenge instructions.

## Corrections to older workspace assumptions

- The active event is online, not the 18–19 October on-site event.
- General Track 2B criteria are not automatically Track 2A or on-site criteria.
- Jurors' “secret scoring”, mentor-selection advantages and projected wins are
  speculation and are not used as evidence.
- English is useful for some documents, but is not one of Switzerland's four
  national languages; Romansh must not be silently replaced with English.
- A found quote is not a calibrated confidence score or proof of semantic accuracy.
- Scans, dates, proposed decisions and question/answer pairing need explicit review.
- The official Apertus 1.5 card currently documents patched serving dependencies.
  No generic local runner, RAM footprint, deployment cost or 70B quality advantage
  on our task is established without testing the actual configuration.
- Numerical targets in earlier specifications are targets, not measurements.
- We will not pre-build an on-site challenge under an assumption that reuse is
  permitted. The on-site cases/rules are separate; our work is for the current
  online window.

The ZHAW brief explicitly says no robot or robotics knowledge is required, but
external API calls are disallowed for its pipeline. The UZH task is scored
automatically, so language fluency is not a prerequisite to competing; its
test split must stay out of development. FHGR specifies consumer-grade GPU
deployment and a limit on model calls per candidate answer. These details
strengthen the alternative comparison beyond the short track titles.

See [the project idea](../PROJECT_IDEA.md) for our proposed scope and schedule,
and [implementation status](../track_2a/docs/BUILD_STATUS.md) for what is actually built.
