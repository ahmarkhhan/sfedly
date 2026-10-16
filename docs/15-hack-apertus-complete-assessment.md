# Skony: Hack Apertus requirements, eligibility, evidence and submission strategy

> Consolidated source assessment and original supplied text. The subsequent
> [project direction](16-project-direction.md) and
> [delivery backlog](18-delivery-backlog.md) now control the build decisions.
> The [source register](17-source-register.md) adds current source checks and
> corrections to earlier project/event references. Preserve the appendices as
> source history rather than treating pasted assistant advice as official rules.

**Reviewed: 15 October 2026, Asia/Karachi.**
**Project:** Skony, `D:\development\Skony\track_2a`.
**Selected challenge:** Online Track 2A / OpenParlData.
**Deadline:** 16 October 2026, 12:00 CEST = **15:00 Pakistan time**.
**Verdict:** Good challenge fit and an implemented extraction/review prototype; **not yet a complete submission**.

This document consolidates the supplied resources, all seven supplied PDFs, the
OpenParlData presentation, relevant linked projects, current official pages, and
the inspected Skony implementation. The appendices preserve the supplied PDF
URLs, guide links, further data/tool links, and the original pasted attachments.
It distinguishes **official requirements**, **provider clarifications**,
**observed project status**, and **recommendations**.

## 1. The most important new finding

The 8 October OpenParlData Q&A explicitly supports a **small, bounded subset**,
prioritising submitted text and government answers. A full representation of
every document feature is not the immediate prerequisite for a defensible partial
result. JSON is a valid format to explore; RDF/XML is discussed as a direction,
not imposed as the only serialization. [OpenParlData Q&A, pp. 1-2][P6]

This refines the earlier [compliance review](14-event-compliance-review.md).
Skony's eight-field scope is not automatically disqualifying. The unresolved
problem is that it has not yet **evaluated that scope across bodies/languages**
or delivered the runnable/public/report package. Implementing every planned
feature before the deadline would be a poor use of the remaining time.

The strongest direction is to demonstrate what a shared request/answer core can
represent, which differences need explicit extensions, and which extractions
must remain under review. This is a recommendation based on the challenge's
published emphasis on insight and applicability. [Challenge brief][OP]

## 2. Eligibility and participation

| Item | Official position / evidence | Implication for this project |
|---|---|---|
| Age | Rules say 18+; overview also says above the legal age of majority in the country of residence. [Rules][RULES] | Check both conditions for each team member. This review does not establish anyone's age. |
| Countries | Devpost lists exclusions: Brazil, Crimea, Cuba, Iran, North Korea, Quebec, Russia. [Rules][RULES] | Pakistan is not on that published list. Individual eligibility still depends on age, residence and registration. |
| Academic affiliation | Event participation is open to technical and nontechnical people. [FAQ][FAQ] | The word “Academia” in Track 2A does not restrict Skony to Swiss university students. |
| Team size | Solo or 1-5 people. [FAQ][FAQ] | Solo submission is allowed. Use consistent membership details in the final form. |
| Registration | Join the event on Devpost and use Discord for communication. [Guide][GUIDE] | Your supplied Devpost text shows a registered account; that is snapshot evidence, not a newly checked account status. |
| Physical attendance | This stage is remote; on-site events are separate. [Event][EVENT] | Liebefeld registration and pitches are not prerequisites for this online submission. |
| AI coding assistants | Explicitly allowed. [FAQ][FAQ] | Using a coding assistant does not itself violate the model rule. |
| Model in the solution | Track 2 must be built with Apertus 1.5. Supporting open-weight models used during development must be disclosed. [Track README][TRACK] | Keep Apertus central to the converter. Document all runtime/supporting models and their roles. |
| Community model builds | The FAQ allows community builds for Track 2; Track 1 uses the official baseline. [FAQ][FAQ] | A text-only/quantized 1.5 build is an option, with exact checkpoint, conversion and quantization disclosed. No migration is necessary for the tested CSCS pilot. |
| Ownership and originality | Submission warranties cover team authorship, work during the event, compatible third-party material and the right to publish. [Terms, section 6][TERMS] | Separate historical plans, dependencies and reference material from original hackathon output. |
| Conduct | Event Code of Conduct applies. [Code of Conduct][CONDUCT] | Participation obligations remain separate from technical scoring. |

**Compute eligibility is a separate issue.** The listed academic compute route
uses partner-institution affiliation; it does not set the eligibility of the
OpenParlData challenge itself. Do not interpret lack of Swiss affiliation as
disqualification from this challenge. [Resources][RESOURCES]

## 3. Timeline, prizes and the actual submission

| Milestone | Published schedule |
|---|---|
| Registration opened | 13 August 2026, 08:00 CEST |
| Online build started | 1 October 2026, 12:00 CEST |
| Final submission | **16 October 2026, 12:00 CEST / 15:00 Asia/Karachi; no extension stated** |
| Jury review | After submission; rules show 16-22 October and guide extends review through 23 October |
| Estimated winners announcement | 23 October 2026, 12:00 CEST; organisers reserve timeline changes |
| Grand Finals | 14 May 2027, St.Gallen |

Sources: [event][EVENT], [rules][RULES], [guide][GUIDE]. Submit early enough to
resolve a rejected upload or inaccessible repository before the closing time.

The published **Academia winner** prize is CHF 2,500 plus $200 Hugging Face
credits and qualification for the Grand Finals. This is a track prize, not a
separate confirmed CHF 2,500 award for every academic challenge. The overall
cash-prize total is not the amount Skony individually wins. [Event prizes][EVENT]

### OpenParlData form fields

The organiser's [submission page][SUBMIT], inspected with **Track 2A -
OpenParlData** selected, requires:

- First name, last name and email used for Devpost registration.
- GitHub username, team name and team members, project name.
- Swiss-student-team selection and model selection.
- **Technical report PDF, maximum six pages.**
- **GitHub repository URL** containing converter, Apertus prompts, validator,
  and README with samples.
- Acceptance of the Terms and Conditions; optional message and optional Hugging
  Face username are also shown.

Submit **once per project** through this form. Devpost registration, a running
localhost page, and a Devpost draft are not the final organiser submission.
The selected OpenParlData form does not require a demo video, five-slide deck,
or a published container-registry URL. Other challenges may require those.
[Selected form][SUBMIT]

### Required package and licences

Keep `track_2a/` as the selected project root, add the Docker-based `make run`,
complete the Markdown report, and supply source/docs/data in the template layout.
Document `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` and actual runtime needs. The
judge run must work on a clean checkout. `data/` is capped at 100 MB.
[Project template][TEMPLATE]

The event's default licences are Apache-2.0 for code/model weights, CC-BY-4.0 for
non-code material, and CDLA-Permissive-2.0 for submitted datasets. Item-level
third-party licences and publication rights must be stated. A source being
publicly downloadable does not establish permission to relicense it.
[Terms, section 6][TERMS]

## 4. What OpenParlData asks Skony to contribute

The challenge has three linked contributions: a reusable affair representation,
an Apertus converter with provenance, and evidence about whether it works across
heterogeneous sources. The published assessment is **insight** plus **breadth
and applicability**, without a numeric weighted rubric in the brief. A
well-founded partial or negative conclusion can count as success. [Brief][OP]

| Contribution | What must be addressed | Useful bounded implementation |
|---|---|---|
| Representation | Documented version, shared meanings and controlled vocabularies; explain how source structure and affair semantics are preserved. | A request/answer core, stable identifiers, raw wording, small normalized vocabulary, explicit extension/unsupported cases. |
| Converter | Real PDFs to valid data using Apertus; retain document/page and text-span evidence where possible. | Preserve original text; verify suggestions; label manual visual transcription and inferred mappings separately. |
| Evidence | Manually checked, multilingual, multi-level sample and at least one cross-parliamentary question. | Reviewed pairs from several bodies, per-field results, concrete failures and a cited comparison over the reviewed subset. |

The presentation's wider semantics include co-signatories, addressed bodies,
procedural history, question/answer pairings, decisions and related-affair links.
It also discusses images, tables and annexes, and possible standards mappings
to Akoma Ntoso, Parla-CLARIN, Popolo and Docling. These are the broader design
ambition. State which parts your prototype supports instead of presenting every
planning item as implemented. [OpenParlData slides][DECK]

### What the Q&A adds

- Prefer an existing affair with attached documents for the initial sample.
- Missing affair numbers and documents without affairs need a declared identity
  policy; do not invent identifiers as extracted facts.
- Document categories and roles are incomplete. A role prediction needs a
  separate inference label.
- Preserve source events/labels and keep harmonization mappings explicit.
- Limit corpus/compute scope; try serial downloads when export requests stall.
- Provider review of a gold set may be requested, subject to availability.

These are clarifications and design guidance, not an additional fixed evaluator
contract. The Q&A's participant-reported missing-number/state counts are
diagnostic observations from that session, not verified current corpus statistics
or Skony results. [Q&A, pp. 1-3][P6]

## 5. Skony compared with the request

### Implemented and evidenced

The local implementation uses strict Pydantic models and eight raw fields.
PDF intake keeps per-page text and a file digest. The Apertus prompt asks for
source wording and quotes, and the verifier rejects unsupported or ambiguous
evidence. All located suggestions still need semantic review.

The workbench offers original page images, evidence highlighting, corrections,
explicit absence, undo, persistent reviews, audit snapshots and reviewed-only
export. The same-day earlier review passed **35 existing engineering tests**.
The source/status files checked for this extended assessment still describe the
same implementation. These tests do not measure real-model extraction accuracy.

Current local evidence: [schema](../track_2a/src/skony/schema.py),
[pipeline](../track_2a/src/skony/pipeline.py),
[verifier](../track_2a/src/skony/verify.py),
[review store](../track_2a/src/skony/review.py),
[server](../track_2a/src/skony/server.py),
[build status](../track_2a/docs/BUILD_STATUS.md),
[pilot report](12-cscs-pilot.md).

The retained real pilot is one two-page German municipal postulate from Nidau.
The 70B call took 7.234 seconds and used 1,725 tokens. The current verifier locates
title, raw type, printed date and request; it withholds the corrupt submitter,
with other missing suggestions null. This does not establish an 8B/70B ranking,
an accuracy percentage, or coverage across parliaments.

### Gaps and their importance

| Gap | Observed difference | Priority / correction |
|---|---|---|
| Docker execution | No Makefile, Dockerfile or Compose configuration in the reviewed project. | **Submission blocker.** Include Python dependencies and Poppler; test on a clean copy. |
| Container networking | Server binds only to `127.0.0.1`; Host/Origin checks assume localhost names. | Packaging detail to test. Configure internal container binding and published host access deliberately. |
| Published reference implementation | Workspace is not a Git checkout; no final public repository URL established. | **Submission blocker.** Publish accessible code with exact run instructions. |
| Public sample package | Pilot data/results are under ignored private/output paths. | Judges will not inherit the local demo. Provide licensed samples, outputs or reproducible retrieval, with hashes/source IDs. |
| Final report | `track_2a/technical_report.md` is an honest draft; no final six-page PDF found. | **Submission blocker.** Finish architecture, evaluation, insights and limitations, then export/verify the PDF. |
| Reviewed evaluation | No real multilingual gold corpus or scoring runner found. | **Core judging gap.** Human-review a bounded comparison and report denominators, failures and coverage. |
| Request/answer linkage | Schema has one question and answer field per PDF, but no implemented affair-level assembly across documents. | Prioritize matched submission/response documents; the Q&A supports this focused core. |
| Controlled vocabulary | Raw type/decision fields are strings, without normalized categories or mapping version. | Add a small documented map; preserve raw values and mark mappings as derived. |
| Identity/context | A PDF hash identifies a document, not necessarily a parliamentary affair; arbitrary uploads lack established affair association. | Keep affair/body identifiers from metadata separate from document identity. Unlinked document policy should be explicit. |
| Semantic completeness | A matching quote can be assigned to the wrong field or omit part of an answer/reasoning. | Evaluate meaning, boundaries and completeness against the authoritative PDF. |
| Multi-page evidence | CandidateField stores a single page and quote. | Long answers need multiple spans or explicit scoped abstention; report this limit. |
| Scans and handwriting | No new OCR pipeline implemented; existing OCR may be corrupted. | Include challenging examples; retain visual correction and measure rejected/unsupported cases. |
| Cross-parliamentary question | No demonstrated comparison across reviewed affairs from different bodies. | Add a simple cited comparison; a chatbot is unnecessary for this deliverable. |
| Source rights | Pilot manifest says redistribution rights are unverified. | Resolve before packaging that document; use another publishable sample if needed. |
| Data size | Current `track_2a/data/` is 7,539,852 bytes (about 7.19 MiB). | Within 100 MB; recheck the published package. Research caches are not the submission dataset. |
| Documentation consistency | Root report claims unimplemented PostgreSQL/FastAPI, commands and placeholder metrics; older judge report covers Liebefeld. | Exclude or prominently archive those files; judges need one accurate entry point. |

No changes to application code, human review decisions, credentials, live model
calls or event submissions were made for this assessment.

## 6. What each supplied slide deck actually concerns

### OpenParlData presentation and Q&A - directly applicable

The presentation explains the representation/extraction/verification problem
and the three contributions above. Its existing workbench means Skony's interface
is a supporting tool; the strongest contribution would be reusable semantics
and measured conversion quality. The follow-up Q&A makes a focused subset more
defensible and highlights incomplete document roles and procedural mappings.
[Presentation][DECK] / [Q&A][P6]

### Apertus 1.5 Under Test - useful experimental guidance

The 41-page session covers academic benchmarks, six business tasks and modality
tests. It reports format/label errors, role confusion, unsupported values,
OCR weaknesses and task-dependent differences between sizes. Its business study
uses English benchmarks and does not establish Swiss parliamentary accuracy.

For Skony, treat the lessons as hypotheses: test missing fields, distinguish
document/actor roles, constrain vocabularies, compare text-first extraction with
image input on difficult pages, and record the exact model/settings. Benchmark
numbers in these slides belong to their tasks; none can become Skony's scores.
Thinking mode should earn its additional tokens and formatting risk through a
controlled comparison. [Slides, especially pp. 17, 21-26, 31-32][P2]

### OST voting-booklet NLI - a separate challenge

This is claim-versus-source classification: 0 entailment, 1 neutral,
2 contradiction, including all nine German/French/Italian pairings. The supplied
31-page intro and 21-page Q&A describe a document task and a provided-reference
task. The later Q&A specifies their 60/40 weighting, macro-F1 qualification
thresholds of 0.60/0.75 respectively, evidence and efficiency scoring, and a
published Linux/amd64 prediction container with its own `BASE_URL`/`API_KEY`
contract. Its starter emits random predictions; it is a contract example rather
than a successful Apertus baseline. [Intro][P1] / [Q&A][P7]

Use its clean evaluator separation and evidence conventions as inspiration.
Its labels, score thresholds, registry requirement and environment names do
**not** replace Skony's OpenParlData requirements. Useful sources: [dataset][OSTDATA],
[starter repository][OSTSTART], [solution API guide][OSTAPI].

### UZH SwissGov-RSD - a separate challenge

The 18-page deck concerns token-level differences between related government
documents in EN-DE, EN-FR and EN-IT pairs. It reports 224 document pairs per
language pairing and uses Spearman correlation as the task metric. Participants
should reproduce the Apertus baseline and protect the test split from
development. The research repository includes commercial-model experiments;
those experiments are not permission to use commercial models for the challenge
solution. [Slides][P5] / [challenge][UZH]

The token annotations measure semantic difference, not parliamentary field
extraction. They cannot serve as Skony's extraction gold set. Sources:
[dataset][UZHDATA], [code][UZHCODE], [Q&A document][UZHQA].

### ZHAW See It, Say It, Pick It - a separate challenge

The 18-page PDF describes camera-image/instruction grounding to a target pixel
and plan, or ask/refuse. Data contain ten scenes and 50 instructions; scoring
weights are 35% grounding, 30% safety, 20% logic, 10% local execution and 5% code.
Apertus handles language reasoning, open vision models may assist, and the
pipeline runs locally without external APIs. [Slides][P3] / [repository][ZHAWCODE]

There are conflicts: slides variously say held-out release on 14 or 15 October,
and say Devpost submission; current repo specifies 14 October and treats the
video as optional. The organiser directs final submissions to its website.
These differences matter to ZHAW entrants; they do not impose robot, local-only,
five-slide, held-out-scene or video obligations on Skony.

### FHGR interview coach - a separate challenge

The 18-page image-based deck was visually read. It concerns age-appropriate
interview coaching, using Apertus 1.5 8B, under 32 GB VRAM and averaging fewer
than five model calls per candidate answer. It distinguishes synthetic development
material from its separate judging benchmark. Its 50/25/25 rubric is performance,
consistency and innovation. [Slides][P4] / [challenge][FHGR]

The interview questions, candidate answers, profiles and didactic rubric are not
Skony evaluation data. A useful transferable lesson is to separate generated
development examples from expert-reviewed labels. The supplied slide does not
establish a public FHGR code-repository URL; none is invented here.

## 7. Resources, demos and tools: use and limitations

| Resource | Relevant use for Skony | Limits / decision |
|---|---|---|
| [Apertus official site][APERTUS] and [8B][MODEL8] / [70B][MODEL70] cards | Exact model identity, chat template, serving dependencies and modality constraints. | Use authored instructions, not autogenerated quickstart panels. Local multimodal serving currently documents custom builds; a working API call does not prove every capability is exposed. |
| [Original Apertus paper][PAPER] | Architecture/training/transparency context. | Explains the original release; cannot substitute for 1.5 documentation or task evaluation. |
| [v1 collection][COLL1] / [v1.5 collection][COLL15] | Distinguish releases and checkpoint names. | Older 1.0/Mini demonstrations are not automatically valid 1.5 submission models. |
| [Data transparency][TRANSPARENCY] | A model for dataset manifests and licensing documentation. | Training transparency is separate from Skony's source-document traceability and data rights. |
| [Swiss Legal RAG Demo][LEGALDEMO] | Small Gradio/RAG example and document retrieval pattern. | README names `Apertus-8B-Instruct-2509`, a Zephyr fallback and hosted HF inference. Adapt version/configuration and remove silent fallback before using it for a 1.5 solution. It provides no Skony evaluation evidence. |
| [Apertus Translate][TRANSLATE] | Human/automatic evaluation workflow and published annotations. | Translation annotations are not parliamentary affair gold data. |
| [Apertus Probes][PROBES] | Longer-term research into internal signals of model errors. | Requires activation access; cannot be assumed available through the current hosted completion API. Check licence before copying code; README licence section is incomplete. |
| [Ticino case study][TICINO] | Concrete example of public-administration use with local infrastructure. | Adoption context, not a Hack Apertus winning project or Skony accuracy benchmark. Article describes rollout/testing; do not inflate that into an independently verified production outcome. |
| [Prompt optimization survey][PROMPTSURVEY] | Background for systematic prompt comparisons. | Prompt search needs a development slice and untouched evaluation slice; optional, not a submission requirement. |
| [Fine-tuning recipes][RECIPES], [PEFT][PEFT], [TRL][TRL], [Alignment Handbook][ALIGN] | Adaptation references if reviewed data and compute justify training. | Fine-tuning is not required for OpenParlData. Adding training now is lower priority than evaluation and packaging. Check version compatibility rather than assuming the generic example works for 1.5. |
| [FHNW Kaggle notebook][KAGGLE] | Listed educational fine-tuning template. | Page was not readable through the web extractor; execution/content not independently verified. No Kaggle job was run. |
| [Andreas Martin text-only 8B][TEXT8] | Author documents standard text-model loading without multimodal towers. | Community derivative, not multimodal official weights. If used, disclose conversion and retest quality; access/licence conditions remain. |
| [Andreas Martin collection][MARTIN] | Experimental embedding/educational variants. | Model cards govern each item; the collection itself is not a tested Skony dependency. |
| [Awesome Apertus][AWESOME] | Additional discovery index for tools, models and providers. | Independent community catalogue, not event rules; verify consequential claims against each primary source. |

### Available support and credits

The [resources page][RESOURCES] says new CSCS requests closed on 6 October,
18:40 CEST, and new Phoeniqs applications closed on 4 October, 20:30 CEST. Use
existing access; do not plan completion around receiving a new allocation.
Hugging Face offers $10 credits through the [event signup][HFCREDITS], excluding
subscription fees. Apply with the Devpost email. Current redemption or allocation
for this account was not checked. The [Ava credit page][AVA] is useful for an
optional demo recording; its terms were not independently retrieved.

A Hugging Face model page or credit balance does not guarantee a particular
model is served by an inference provider. Nor does an open Swiss model establish
the geographic location of hosted inference. Skony should document its tested
endpoint and the actual deployment/data flow. [Model card][MODEL8]

### People and clarification channels

Use [event Discord][DISCORD] and [mentors][MENTORS] for scope/evaluation advice.
The OpenParlData Q&A names **Christian Gutknecht / info@openparldata.ch** for
data-model questions and possible gold-set review. Review availability is not
promised. Useful specific questions would concern document-to-affair linking,
request/answer roles and vocabulary mappings. This assessment sends no messages,
books no sessions and requests no editor rights. [Q&A][P6]

There is no published basis for claiming that contacting a mentor increases a
jury score. Mentor descriptions are guidance on whom to ask, not secret judging
criteria.

## 8. Data and standards that matter to Skony

| Source | Use | Sampling / access decision |
|---|---|---|
| [OpenParlData API docs][APIDOC] | Affair/body/contributor/event metadata and source links. | Preserve API IDs; metadata is context, not automatic PDF field ground truth. Swagger page was available but not fully extracted as text. |
| [Bulk exports][EXPORTS] | Bounded metadata snapshot and source selection. | Download only necessary body/document slices; full exports are far beyond the submission cap. |
| [Original PDFs][PDFFILES] | Authoritative extraction and review sources. | Record URL, body/affair/document IDs, checksum and retrieval date. |
| [Admin workbench][ADMIN] | Existing provider workflow; potential editor access by request. | Shows why integration-ready schema/converter evidence matters. Authentication/editor actions were not taken. |
| [eCH political-affairs group][ECH] | Terminology/standardization reference. | Slides and Q&A describe ongoing work; do not claim conformity to a completed unverified standard. |
| [OST voting data][OSTDATA] and [Federal Chancellery collection][BOOKLETS] | Separate booklet-NLI benchmark. | Useful method comparison; not a replacement for affair extraction labels. |
| [SwissGov-RSD][UZHDATA] | Separate cross-language-difference benchmark. | Its gold annotation task is different from Skony's. |
| [ZHAW dataset/code][ZHAWCODE] | Separate robot-image benchmark. | Outside Skony's corpus and output contract. |

### Proposed sample design - recommendation, not an official count

Aim for **12-20 reviewed documents**, subject to genuine review capacity, spanning
at least three bodies, German and French, at least two government levels, and
more than one document role. Include matched requests/responses where available,
with some born-digital and difficult OCR/scanned examples. The event sets no
fixed minimum document count for this challenge. A smaller honest sample is
preferable to more unreviewed documents; it also supports only narrower claims.

Select the documents before comparing prompts. Split by **affair/document group**
so a response, duplicate file or translated version of a development affair does
not appear in the final evaluation. Record exclusions and failures. Keep a
small untouched evaluation slice and publish the selection method.

Gold annotations should use the original PDF, not merely its OCR. For each field
record value, supporting page/spans, role/boundary and review reason. Distinguish
**absent from this document**, **unreadable**, **not yet extracted** and **present
in another document**. An absent answer in a request PDF does not prove the
affair was never answered. Machine-generated or automated-interface test
decisions must never be silently promoted to gold labels.

## 9. How Skony can strengthen its chances

No probability of winning can be established from the available material. The
recommendations below follow the published OpenParlData assessment, not inferred
personal preferences of jurors.

### A. Deliver an actual feasibility finding

Frame one question: **Which request/answer fields can share a representation
across our sampled parliaments while preserving meaning and traceability?**
Present a table of shared fields, per-body differences and unsupported cases.
If a unified procedural-state enum loses meaning, preserve events/source labels
and demonstrate that limitation. A measured boundary is more useful than a
claim of universal compatibility.

### B. Make provenance necessary but measure semantics separately

Skony already has an engineering strength: it checks whether an output can be
located. Add evidence of whether that located text is **the right field** and
complete for the declared scope. Include at least one example of a true quote
assigned to the wrong role, a garbled name, a split-page response, and an absent
value. Show what the verifier catches and what requires human review.

### C. Compare a simple baseline fairly

Use the same frozen reviewed sample for a simple Apertus prompt, the structured
prompt, and the structured prompt plus deterministic checks. Keep model identity
and input context comparable. A text-parser/rule baseline may also help where
fields have explicit headings. Baseline comparison is a recommended way to
support insight; the OpenParlData brief does not specify an official numeric
baseline to beat.

Report schema-valid rate, semantic field correctness, present-field recall,
explicit abstention/coverage, incorrect unsupported values, evidence accuracy,
request/answer completeness and linking errors. Include per-language/body slices,
document counts, all failures and token/latency observations. Do not report only
successful parsed calls or use source-location rate as semantic accuracy.

### D. Show a real cross-parliamentary question

Choose a question supported by the sampled records, such as which sampled
parliaments submitted questions on a common subject and how their executives
responded. Use a table of body, affair/date, request, response and evidence
links. Keep proposals separate from decisions and government answers separate
from submitter reasoning. State that the answer covers **the sampled corpus**,
not all Swiss parliaments. A deterministic query over reviewed data can be enough;
generative chat adds work without being required.

### E. Make the reviewer's first run dependable

Package a sample that can load without private local files, retain recorded
outputs with accurate labels, and offer a configurable live Apertus converter.
Clearly distinguish offline replay from live inference. A replay helps the demo,
but does not replace an implemented live converter or disclose its current
runtime/API requirements by itself.

### F. Write the report around results

Use the six-page allowance for scope, schema decisions, pipeline/provenance,
evaluation, observed differences and limitations. Keep an appendix in the repo
for prompts, labels, data sources, run records and detailed errors. Include an
honest partial/negative finding if supported. The existing draft's candid
limitations are preferable to the root report's placeholder metrics.

## 10. Recommended completion order

| Order | Work | Concrete completion evidence |
|---|---|---|
| 1 | Freeze the request/answer scope and sample. | Declared fields, document roles, inclusion criteria and source/rights manifest. |
| 2 | Add the judge runner and public sample path. | `make run` from a clean copy, rendered PDF/evidence, working converter, documented model configuration. |
| 3 | Finish human annotations and score the sample. | Frozen labels, raw runs, scorer and result tables with failures. |
| 4 | Add a minimal vocabulary/linking representation. | Versioned raw/derived fields, matched affairs/documents, explained unsupported cases. |
| 5 | Answer one cross-body question. | Reviewed rows, original evidence and coverage statement. |
| 6 | Finish repository, licences and PDF report. | Accessible public URL, samples, source instructions, six-page-or-shorter PDF with no placeholders. |
| 7 | Submit before 15:00 Pakistan time on 16 October. | Organiser form completed once; acceptance/receipt checked by the submitting team. |

Reserve time for submission and clean-copy checks. Treat new interface features,
training runs, large corpus downloads, elaborate RAG and a full knowledge graph
as lower priority until the evidence and required artifacts exist. This is a
delivery recommendation, not an event rule.

## 11. Differences and contradictions to keep visible

| Statement / material | Correct interpretation for Skony |
|---|---|
| “Build every feature of the broad schema before entering.” | Q&A supports a smaller core; bound it and produce evidence. Broad schema ambition remains a design/evaluation topic. |
| “RDF/XML is mandatory.” | Serialization is part of the exploration; JSON is not excluded. |
| “Use PostgreSQL/FastAPI/Angular to qualify.” | Provider stack is a reference; language/framework choice is unrestricted for OpenParlData. |
| “Run all 300,000 affairs.” | Provider encourages sampled development; submission data cap remains 100 MB. |
| “Every Swiss language is a fixed minimum for Skony.” | Brief asks for multilingual breadth; no mandatory four-language minimum is published for OpenParlData. DE/FR is a recommended starting sample, not proof of all-language coverage. |
| “Both 8B and 70B must be used.” | OpenParlData permits 8B or 70B; comparing both is optional if useful and fair. |
| “No external API for any Track 2 project.” | This is a ZHAW constraint. Skony's documented Apertus endpoint is consistent with its challenge approach. |
| “Macro-F1 must exceed 0.60/0.75.” | Those are the OST Q&A qualification gates, not Skony's score thresholds. |
| “Publish a registry image and use BASE_URL/API_KEY.” | OST-specific runner contract; Skony follows the template's `LLM_*` and Docker `make run`. |
| “Five slides and a video are required for Skony.” | Not in the selected OpenParlData form. ZHAW materials have their own presentation requirements. |
| “Submit on Devpost.” | Some older slides say this; current event/template/form direct final submission to the organiser's website. |
| “The Guide's registration link points to the right event.” | Supplied guide includes `genaizurich.devpost.com`; use the event-specific `hackapertus.devpost.com`. |
| “A resource-listed demo is a compliant finished project.” | Some use older models, extra models, different output contracts or synthetic/random examples. Inspect before reuse. |
| “A trained-on-open-data model licenses our PDFs.” | Model and source-document rights are separate. |
| “35 tests passing demonstrates accuracy.” | Engineering validation only; real reviewed extraction results remain outstanding. |
| “Four fields located means 50% accuracy.” | Location, presence and correctness have different denominators; this percentage would be misleading. |
| “The pilot's null answer shows the affair has no response.” | The current PDF is a request; other documents may contain a response. |
| “The public gallery gives a competitor ranking.” | Gallery was unpublished when checked; no track ranking/win prediction can be derived. |

## 12. Review coverage and limitations

All **seven supplied PDFs were successfully downloaded**. Text was extracted
from text-bearing pages; the image-based FHGR deck was visually read, and
important charts/image-only benchmark pages were rendered and inspected.
The original signed URLs initially failed in the web extractor but worked as
direct public downloads. Their embedded expiry is **15 October 2026, 06:00 UTC /
11:00 Pakistan time**. Use the official slides catalogue to obtain fresh links
after expiry rather than treating these URLs as permanent.

The public resources catalogue, recording catalogue and FAQ answers were read in
the rendered browser. The selected submission form, challenge brief and terms
were read during the same-day preceding review. Existing guide-child snapshots
are reused and labelled as source snapshots, not newly watched sessions.
Public technical repositories/model cards/data landing pages were checked where
readable. No referenced example project was executed or installed.

Zoom recordings are **catalogued, not watched or transcribed**. Their information
sessions are covered by the supplied slides; no extra verbal instructions are
asserted. The Kaggle notebook and Ava credit page were not fully readable through
the web extractor. Participant browsing is sign-in-gated; the project gallery
was unpublished. Personal portfolio/settings/notification links and platform
footer/branding links are preserved for completeness but are not challenge
evidence. Do not describe those destinations as fully audited.

The following appendices are a link archive and source context, not an
endorsement of every external resource or a public redistribution licence for
the downloaded research cache.

<!-- SOURCE_APPENDICES -->

## Appendix A. Supplied PDF archive

All seven files were retrieved successfully. Links below retain the supplied signed
parameters; the catalogue is the durable starting point after their expiry.

[Official recordings and slides catalogue](https://hackapertus.notion.site/3f0b4fec112a80a79522fd9539171c91?v=3f0b4fec112a80e4a556000cbc8efaf6&pvs=18).

| Source | Pages | Reading method | Link |
|---|---:|---|---|
| P1: OST NLI introductory slides | 31 | Text read; relevant visuals checked | [Supplied PDF][P1] |
| P2: Apertus 1.5 Under Test | 41 | Text read; relevant visuals checked | [Supplied PDF][P2] |
| P3: ZHAW robot grounding | 18 | Complete extracted text read | [Supplied PDF][P3] |
| P4: FHGR interview coach and datasets | 18 | All pages visually read (image-based PDF) | [Supplied PDF][P4] |
| P5: UZH SwissGov-RSD | 18 | Text read; relevant visuals checked | [Supplied PDF][P5] |
| P6: OpenParlData Q&A, 8 October | 3 | Text read; relevant visuals checked | [Supplied PDF][P6] |
| P7: OST Q&A, 8 October | 21 | Complete extracted text read | [Supplied PDF][P7] |

## Appendix B. Main sources and relevance

The identifiers correspond to links used above. “Read” means source content was
inspected, not that the software was executed or a model/data file was installed.

| ID | Source | Review / relevance |
|---|---|---|
| EVENT | [EVENT](https://hackapertus.devpost.com/) | Read |
| RULES | [RULES](https://hackapertus.devpost.com/rules) | Read |
| FAQ | [FAQ](https://hackapertus.ch/faq#online-hackathon) | Read |
| GUIDE | [GUIDE](https://hackapertus.notion.site/getting-started-guide-onlinehack) | Official/source snapshot read; not newly fully retrieved |
| TRACK | [TRACK](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md) | Read |
| TEMPLATE | [TEMPLATE](https://github.com/HackApertus/project-template) | Read |
| TERMS | [TERMS](https://hackapertus.ch/terms-and-conditions) | Rendered source read in same-day preceding review |
| CONDUCT | [CONDUCT](https://hackapertus.ch/code-of-conduct) | Official/source snapshot read; not newly fully retrieved |
| RESOURCES | [RESOURCES](https://hackapertus.notion.site/resources-tools) | Read |
| SUBMIT | [SUBMIT](https://hackapertus.ch/online-hack/submissions) | Rendered source read in same-day preceding review |
| OP | [OP](https://hackapertus.notion.site/track-2a-openparldata) | Rendered source read in same-day preceding review |
| DECK | [DECK](https://hackapertus-document-extraction-26a562.gitlab.io/#/title-slide) | Read |
| OSTDATA | [OSTDATA](https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets) | Read |
| OSTSTART | [OSTSTART](https://gitlab.com/ifsoftware/hackapertus-starter) | Read |
| OSTAPI | [OSTAPI](https://hackapertus.notion.site/solution-api-guide-ef5b4fec112a834da43101ede56300f5) | Linked by OST Q&A; detailed guide not independently read |
| UZH | [UZH](https://hackapertus.notion.site/track-2a-uzh) | Official/source snapshot read; not newly fully retrieved |
| UZHDATA | [UZHDATA](https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD) | Read |
| UZHCODE | [UZHCODE](https://github.com/ZurichNLP/SwissGov-RSD) | Read |
| UZHQA | [UZHQA](https://docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/edit?usp=sharing) | Read |
| ZHAWCODE | [ZHAWCODE](https://github.com/Fatemeh-MA/see-it-say-it-pick-it) | Read |
| FHGR | [FHGR](https://hackapertus.notion.site/track-2a-fhgr) | Official/source snapshot read; not newly fully retrieved |
| APERTUS | [APERTUS](https://www.apertus-ai.org/) | Read |
| MODEL8 | [MODEL8](https://huggingface.co/swiss-ai/Apertus-v1.5-8B) | Read |
| MODEL70 | [MODEL70](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) | Read |
| PAPER | [PAPER](https://arxiv.org/abs/2509.14233) | Read |
| COLL1 | [COLL1](https://huggingface.co/collections/swiss-ai/apertus-v1) | Linked; full page not retrieved |
| COLL15 | [COLL15](https://huggingface.co/collections/swiss-ai/apertus-v15) | Read |
| TRANSPARENCY | [TRANSPARENCY](https://github.com/swiss-ai/apertus-data-transparency) | Read |
| LEGALDEMO | [LEGALDEMO](https://github.com/alexchilton/apertus_demo_hf) | Read |
| TRANSLATE | [TRANSLATE](https://github.com/swiss-ai/apertus-translate) | Read |
| PROBES | [PROBES](https://github.com/swiss-ai/apertus-probes) | Read |
| TICINO | [TICINO](https://apertus-ai.org/articles/2026-03-ticino/) | Read |
| PROMPTSURVEY | [PROMPTSURVEY](https://arxiv.org/abs/2502.16923) | Read |
| RECIPES | [RECIPES](https://github.com/swiss-ai/apertus-finetuning-recipes) | Read |
| PEFT | [PEFT](https://huggingface.co/docs/peft/index) | Read |
| TRL | [TRL](https://huggingface.co/docs/trl/sft_trainer) | Read |
| ALIGN | [ALIGN](https://github.com/huggingface/alignment-handbook) | Read |
| KAGGLE | [KAGGLE](https://www.kaggle.com/code/andreasmartinch/sft-apertus-v1-5-8b-hack-apertus-template) | Linked; full page not retrieved |
| TEXT8 | [TEXT8](https://huggingface.co/andreasmartin/apertus-v1.5-8b-text) | Read |
| MARTIN | [MARTIN](https://huggingface.co/collections/andreasmartin/apertus) | Read |
| AWESOME | [AWESOME](https://github.com/rnckp/awesome-apertus) | Independent discovery list read; not event authority |
| HFCREDITS | [HFCREDITS](https://hackapertus.ch/online-hack/hugging-face) | Offer read in resources; no account redemption checked |
| AVA | [AVA](https://avlana.notion.site/Getting-Free-Credits-for-EditWithAva-3de3bdc93da0801d8934df4d9c8efd42) | Linked; full page not retrieved |
| DISCORD | [DISCORD](https://discord.gg/hack-apertus) | Read |
| MENTORS | [MENTORS](https://hackapertus.notion.site/mentors) | Official/source snapshot read; not newly fully retrieved |
| APIDOC | [APIDOC](https://api.openparldata.ch/documentation) | Swagger landing page checked; API specification not fully audited |
| EXPORTS | [EXPORTS](https://files.openparldata.ch/exports/) | Read |
| PDFFILES | [PDFFILES](https://files.openparldata.ch/doc/) | Source address in provider material; private/admin actions not taken |
| ADMIN | [ADMIN](https://admin.openparldata.ch/) | Source address in provider material; private/admin actions not taken |
| ECH | [ECH](https://www.ech.ch/de/der-verein/fachgruppen/politische-geschaefte) | Read |
| BOOKLETS | [BOOKLETS](https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978) | Read |

## Appendix C. Supplied guide links and recovered public equivalents

The original pasted guide uses app.notion.com links; public equivalents were
recorded in the existing research snapshots. Preserve both so a copied slug or
old event hyperlink cannot silently change the event being reviewed.

| Page | Original supplied address | Reviewed/public source |
|---|---|---|
| Registration | [Supplied](https://app.notion.com/Registration-on-Devpost-6d6b4fec112a827586b401bee7161bf4?pvs=21) | [Public source](https://hackapertus.notion.site/Registration-on-Devpost-6d6b4fec112a827586b401bee7161bf4?pvs=25) |
| Schedule | [Supplied](https://app.notion.com/Schedule-9c6b4fec112a82b3aeb1817a8c290d82?pvs=21) | [Public source](https://hackapertus.notion.site/Schedule-9c6b4fec112a82b3aeb1817a8c290d82?pvs=25) |
| Online sessions | [Supplied](https://app.notion.com/Online-sessions-761b4fec112a825081b38164055caa2a?pvs=21) | [Public source](https://hackapertus.notion.site/Online-sessions-761b4fec112a825081b38164055caa2a?pvs=25) |
| Communication | [Supplied](https://app.notion.com/Communication-Channels-a74b4fec112a83e9a59481a6ce22c450?pvs=21) | [Public source](https://hackapertus.notion.site/Communication-Channels-a74b4fec112a83e9a59481a6ce22c450?pvs=25) |
| Team formation | [Supplied](https://app.notion.com/How-to-team-up-21eb4fec112a8298b29e81c636999ff5?pvs=21) | [Public source](https://hackapertus.notion.site/how-to-team-up?pvs=25) |
| Track 1 | [Supplied](https://app.notion.com/Challenges-Track-1-Apertus-Readiness-e41b4fec112a825bb79201853e342d16?pvs=21) | [Public source](https://hackapertus.notion.site/challenges-track-1-apertus-readiness?pvs=25) |
| Track 2 | [Supplied](https://app.notion.com/Challenges-Track-2-Apertus-Adoption-3d7b4fec112a80e498d3cae4e3de4b27?pvs=21) | [Public source](https://hackapertus.notion.site/track-2-apertus-adoption?pvs=25) |
| Resources | [Supplied](https://app.notion.com/Resources-Tools-0e9b4fec112a8380989881f264af0895?pvs=21) | [Public source](https://hackapertus.notion.site/resources-tools?pvs=25) |
| Partners | [Supplied](https://app.notion.com/Hackathon-Partners-8e5b4fec112a8377b252011374b046dc?pvs=21) | [Public source](https://hackapertus.notion.site/Hackathon-Partners-8e5b4fec112a8377b252011374b046dc?pvs=25) |
| Mentors | [Supplied](https://app.notion.com/Mentors-fe7b4fec112a8342ad42810975340907?pvs=21) | [Public source](https://hackapertus.notion.site/mentors?pvs=25) |
| Jury/awards | [Supplied](https://app.notion.com/Jury-Awards-adeb4fec112a82d58cbc8131e21ca274?pvs=21) | [Public source](https://hackapertus.notion.site/Jury-Awards-adeb4fec112a82d58cbc8131e21ca274?pvs=25) |
| Submission guide | [Supplied](https://app.notion.com/How-to-Submit-a-Project-c91b4fec112a82f6adcf81c67c2acde3?pvs=21) | [Public source](https://hackapertus.notion.site/how-to-submit-a-project?pvs=25) |
| Recordings/slides | [Supplied](https://app.notion.com/3f0b4fec112a80a79522fd9539171c91?pvs=21) | [Public source](https://hackapertus.notion.site/3f0b4fec112a80a79522fd9539171c91?v=3f0b4fec112a80e4a556000cbc8efaf6&pvs=18) |

Additional supplied registration link: [genaizurich.devpost.com](https://genaizurich.devpost.com/)
(another event hostname; use [Hack Apertus](https://hackapertus.devpost.com/) for this submission).

[On-site series](https://app.sprintd.org/series/hack-apertus) is a separate phase; its cases and eligibility were not applied to Skony.

## Appendix D. Session recordings and further links

Recordings are inventoried below and have not been watched or transcribed.
Challenge-channel invitations and Q&A files are support destinations; no messages
were sent. Historical session-registration links do not register the final project.

- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-02.txt, challenge-03.txt, challenge-04.txt, challenge-06.txt, challenge-07.txt, guide-04.txt, guide-06.txt, guide-07.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)![Image](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)![Image) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)02](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)02) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)08](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)08) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)2](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)2) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)Getting](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)Getting) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)┃team-formation](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)┃team-formation) - Linked reference / source snapshot; see coverage limits above. Origin: guide-03.txt, guide-04.txt.
- [localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)︱ask-organisers](http://localhost/2ae2cc6f0544e8fcceb52fb6a599a7ea)︱ask-organisers) - Linked reference / source snapshot; see coverage limits above. Origin: guide-03.txt.
- [aclanthology.org/2026.acl-long.1437.pdf](https://aclanthology.org/2026.acl-long.1437.pdf) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt.
- [admin.openparldata.ch/](https://admin.openparldata.ch/#/extraction?tab=documents_stg&body=743&table=743_archive_affairs) - Linked reference / source snapshot; see coverage limits above. Origin: guide-13.txt.
- [apertus-ai.org/docs/tech/fine-tuning/](https://apertus-ai.org/docs/tech/fine-tuning/) - Linked reference / source snapshot; see coverage limits above. Origin: primary model adaptation instructions.
- [blog.nlp-lab.ai/](https://blog.nlp-lab.ai/) - Linked reference / source snapshot; see coverage limits above. Origin: apertus-under-test PDF p.33.
- [blog.nlp-lab.ai/2025/09/05/ApertusBench.html](https://blog.nlp-lab.ai/2025/09/05/ApertusBench.html) - Linked reference / source snapshot; see coverage limits above. Origin: apertus-under-test PDF p.4.
- [blog.nlp-lab.ai/2026/07/29/Apertus15Bench.html](https://blog.nlp-lab.ai/2026/07/29/Apertus15Bench.html) - Linked reference / source snapshot; see coverage limits above. Origin: apertus-under-test PDF p.14, apertus-under-test PDF p.4.
- [blog.nlp-lab.ai/2026/10/01/Apertus1-5-BusinessBenchmarks.html](https://blog.nlp-lab.ai/2026/10/01/Apertus1-5-BusinessBenchmarks.html) - Linked reference / source snapshot; see coverage limits above. Origin: Under Test references; extractor failed.
- [blog.nlp-lab.ai/2026/10/01/Apertus15GettingStarted.html](https://blog.nlp-lab.ai/2026/10/01/Apertus15GettingStarted.html) - Linked reference / source snapshot; see coverage limits above. Origin: apertus-under-test PDF p.13.
- [creativecommons.org/licenses/by/4.0/](https://creativecommons.org/licenses/by/4.0/) - Linked reference / source snapshot; see coverage limits above. Origin: guide-13.txt.
- [cscs.ch/science/computer-science-hpc/2026/apertus-powers-in-house-ai-translation-for-ticino](https://cscs.ch/science/computer-science-hpc/2026/apertus-powers-in-house-ai-translation-for-ticino) - Linked reference / source snapshot; see coverage limits above. Origin: original catalogue link; recovered through official Apertus article.
- [discord.gg/NRYuDCmyU](https://discord.gg/NRYuDCmyU) - Support invitation; no private channel content read. Origin: guide-06.txt.
- [discord.gg/bfmRY36n3](https://discord.gg/bfmRY36n3) - Support invitation; no private channel content read. Origin: challenge-04.txt, guide-06.txt.
- [discord.gg/hack-apertus),y](https://discord.gg/hack-apertus),y) - Support invitation; no private channel content read. Origin: guide-03.txt.
- [discord.gg/zb8DG43u7](https://discord.gg/zb8DG43u7) - Support invitation; no private channel content read. Origin: guide-06.txt.
- [docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/edit](https://docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/edit?tab=t.0) - Linked reference / source snapshot; see coverage limits above. Origin: uzh-slides PDF p.16.
- [docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/edit](https://docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/edit?usp=sharing)(you) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt.
- [files.openparldata.ch/](https://files.openparldata.ch/) - Linked reference / source snapshot; see coverage limits above. Origin: guide-13.txt.
- [github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md](https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md) - Linked reference / source snapshot; see coverage limits above. Origin: ost-slides PDF p.29.
- [github.com/swiss-ai/apertus-legal/blob/main/apertus_1.5/PRIVACY_POLICY.pdf](https://github.com/swiss-ai/apertus-legal/blob/main/apertus_1.5/PRIVACY_POLICY.pdf) - Linked reference / source snapshot; see coverage limits above. Origin: model card conditions; not newly fully read.
- [github.com/swiss-ai/apertus-legal/blob/main/apertus_1.5/USAGE_POLICY.pdf](https://github.com/swiss-ai/apertus-legal/blob/main/apertus_1.5/USAGE_POLICY.pdf) - Linked reference / source snapshot; see coverage limits above. Origin: model card conditions; not newly fully read.
- [hackapertus.ch/online-hack/kickoff-deck](https://hackapertus.ch/online-hack/kickoff-deck?slide=1) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [hackapertus.devpost.com/forum_topics/45510-urgent-free-apertus-1-5-inference-credits-or-gpu-access-for-hackathon-participants](https://hackapertus.devpost.com/forum_topics/45510-urgent-free-apertus-1-5-inference-credits-or-gpu-access-for-hackathon-participants) - Linked reference / source snapshot; see coverage limits above. Origin: public participant discussion; not organiser policy.
- [hackapertus.notion.site/3f0b4fec112a80a79522fd9539171c91](https://hackapertus.notion.site/3f0b4fec112a80a79522fd9539171c91?v=3f0b4fec112a80e4a556000cbc8efaf6&pvs=18) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [hackapertus.notion.site/83ab4fec112a82a6b420019923b8faeb](https://hackapertus.notion.site/83ab4fec112a82a6b420019923b8faeb?v=0bdb4fec112a8369bff908458e303058&pvs=18) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [hackapertus.notion.site/Communication-Channels-a74b4fec112a83e9a59481a6ce22c450](https://hackapertus.notion.site/Communication-Channels-a74b4fec112a83e9a59481a6ce22c450?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: guide-03.txt.
- [hackapertus.notion.site/Jury-Awards-adeb4fec112a82d58cbc8131e21ca274](https://hackapertus.notion.site/Jury-Awards-adeb4fec112a82d58cbc8131e21ca274?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: guide-10.txt.
- [hackapertus.notion.site/Online-sessions-761b4fec112a825081b38164055caa2a](https://hackapertus.notion.site/Online-sessions-761b4fec112a825081b38164055caa2a?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: guide-02.txt.
- [hackapertus.notion.site/getting-started-guide-onlinehack](https://hackapertus.notion.site/getting-started-guide-onlinehack?pvs=18) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [hackapertus.notion.site/how-to-team-up](https://hackapertus.notion.site/how-to-team-up?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: guide-04.txt.
- [hackapertus.notion.site/p/fe7b4fec112a8342ad42810975340907](https://hackapertus.notion.site/p/fe7b4fec112a8342ad42810975340907?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-03.txt, challenge-04.txt, challenge-05.txt, challenge-06.txt.
- [hackapertus.notion.site/resources-tools](https://hackapertus.notion.site/resources-tools?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: guide-07.txt.
- [hackapertus.notion.site/track-2-apertus-adoption](https://hackapertus.notion.site/track-2-apertus-adoption?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [hackapertus.notion.site/track-2-b-own-project](https://hackapertus.notion.site/track-2-b-own-project?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-07.txt, guide-06.txt.
- [hackapertus.notion.site/track-2a-fhgr](https://hackapertus.notion.site/track-2a-fhgr?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-02.txt, guide-06.txt.
- [hackapertus.notion.site/track-2a-openparldata](https://hackapertus.notion.site/track-2a-openparldata?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-03.txt, guide-06.txt.
- [hackapertus.notion.site/track-2a-ost](https://hackapertus.notion.site/track-2a-ost?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-04.txt, guide-06.txt.
- [hackapertus.notion.site/track-2a-uzh](https://hackapertus.notion.site/track-2a-uzh?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt, guide-06.txt.
- [hackapertus.notion.site/track-2a-zhaw](https://hackapertus.notion.site/track-2a-zhaw?pvs=25) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-06.txt, guide-06.txt.
- [huggingface.co/collections/swiss-ai/apertus-v1)&[v1.5](https://huggingface.co/collections/swiss-ai/apertus-v15](https://huggingface.co/collections/swiss-ai/apertus-v1)&[v1.5](https://huggingface.co/collections/swiss-ai/apertus-v15) - Linked reference / source snapshot; see coverage limits above. Origin: guide-07.txt.
- [huggingface.co/docs/hub/spaces](https://huggingface.co/docs/hub/spaces) - Linked reference / source snapshot; see coverage limits above. Origin: resources catalogue.
- [huggingface.co/docs/inference-endpoints/main/en/index](https://huggingface.co/docs/inference-endpoints/main/en/index) - Linked reference / source snapshot; see coverage limits above. Origin: resources catalogue.
- [huggingface.co/docs/inference-providers](https://huggingface.co/docs/inference-providers) - Linked reference / source snapshot; see coverage limits above. Origin: resources catalogue.
- [huggingface.co/docs/peft/index)&[TRL](https://huggingface.co/docs/trl/sft_trainer](https://huggingface.co/docs/peft/index)&[TRL](https://huggingface.co/docs/trl/sft_trainer) - Linked reference / source snapshot; see coverage limits above. Origin: guide-07.txt.
- [huggingface.co/settings/jobs](https://huggingface.co/settings/jobs) - Linked reference / source snapshot; see coverage limits above. Origin: resources catalogue; account settings not inspected.
- [huggingface.co/swiss-ai/Apertus-v1.5-8B)[huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-8B)[huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-07.txt.
- [luma.com/18oeqo3d](https://luma.com/18oeqo3d) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt.
- [luma.com/18oeqo3d](https://luma.com/18oeqo3d](https://luma.com/18oeqo3d](https://luma.com/18oeqo3d) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/3avq28dg](https://luma.com/3avq28dg) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-03.txt.
- [luma.com/3avq28dg](https://luma.com/3avq28dg](https://luma.com/3avq28dg](https://luma.com/3avq28dg) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/dxtzhae0](https://luma.com/dxtzhae0) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-02.txt.
- [luma.com/dxtzhae0](https://luma.com/dxtzhae0](https://luma.com/dxtzhae0](https://luma.com/dxtzhae0) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/fmpw0ej9](https://luma.com/fmpw0ej9) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-06.txt.
- [luma.com/fmpw0ej9](https://luma.com/fmpw0ej9](https://luma.com/fmpw0ej9](https://luma.com/fmpw0ej9) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/g7mccjtk)![Image](https://luma.com/g7mccjtk)![Image) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-02.txt.
- [luma.com/g7mccjtk](https://luma.com/g7mccjtk](https://luma.com/g7mccjtk](https://luma.com/g7mccjtk) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/mne4e0m5)![Image](https://luma.com/mne4e0m5)![Image) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-03.txt.
- [luma.com/mne4e0m5](https://luma.com/mne4e0m5](https://luma.com/mne4e0m5](https://luma.com/mne4e0m5) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/nkvf2m7y](https://luma.com/nkvf2m7y) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-04.txt.
- [luma.com/nkvf2m7y](https://luma.com/nkvf2m7y](https://luma.com/nkvf2m7y](https://luma.com/nkvf2m7y) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/qz7x62m8](https://luma.com/qz7x62m8) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-04.txt.
- [luma.com/qz7x62m8](https://luma.com/qz7x62m8](https://luma.com/qz7x62m8](https://luma.com/qz7x62m8) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [luma.com/sxg60smd)![Image](https://luma.com/sxg60smd)![Image) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-06.txt.
- [luma.com/sxg60smd](https://luma.com/sxg60smd](https://luma.com/sxg60smd](https://luma.com/sxg60smd) - Linked reference / source snapshot; see coverage limits above. Origin: guide-02.txt, guide-06.txt.
- [luma.com/zadclwjh](https://luma.com/zadclwjh) - Linked reference / source snapshot; see coverage limits above. Origin: challenge-05.txt.
- [luma.com/zadclwjh](https://luma.com/zadclwjh](https://luma.com/zadclwjh](https://luma.com/zadclwjh) - Linked reference / source snapshot; see coverage limits above. Origin: guide-06.txt.
- [openparldata.ch](https://openparldata.ch) - Linked reference / source snapshot; see coverage limits above. Origin: guide-13.txt.
- [orcid.org/0000-0002-7265-1692](https://orcid.org/0000-0002-7265-1692) - Linked reference / source snapshot; see coverage limits above. Origin: guide-13.txt.
- [us06web.zoom.us/rec/share/1akxH8UG0k90MSoWCrlpK3R1RaNrSHCvZZmZti1XXH5Cn66xOOBEMFMXX4ylHnkl.W5dSnDb1tQebGWo3](https://us06web.zoom.us/rec/share/1akxH8UG0k90MSoWCrlpK3R1RaNrSHCvZZmZti1XXH5Cn66xOOBEMFMXX4ylHnkl.W5dSnDb1tQebGWo3) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/3uiD_VjOj31U480MyR-fXyABwmn2hYaCdgloRXv82CSysnsFmWyG1KH6PpDswIxF.EOrcEzlD9638N9S_](https://us06web.zoom.us/rec/share/3uiD_VjOj31U480MyR-fXyABwmn2hYaCdgloRXv82CSysnsFmWyG1KH6PpDswIxF.EOrcEzlD9638N9S_) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/BikodDcag-VBXzQhWz_dABkiBr9k4OOMauLMqCDJo63mIvHexhh2sIRmreya09K3.OPYFwxrugC2h6NAj](https://us06web.zoom.us/rec/share/BikodDcag-VBXzQhWz_dABkiBr9k4OOMauLMqCDJo63mIvHexhh2sIRmreya09K3.OPYFwxrugC2h6NAj) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/FoWraXw30hZecrvlxVYwAQSCz1zpr8MN2O6B0IA2nWWMb_XkJfPEcCtx4KabBqZw.lJtfydQ66sns0jw8](https://us06web.zoom.us/rec/share/FoWraXw30hZecrvlxVYwAQSCz1zpr8MN2O6B0IA2nWWMb_XkJfPEcCtx4KabBqZw.lJtfydQ66sns0jw8) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/JSJmCwaKlcIzR6M9Pp3WOhpK0yJGWj5NLqKRDSbHd62UbDg_D8VHnPgPy3NHVsCq.V-slDbbdgQ6zajhY](https://us06web.zoom.us/rec/share/JSJmCwaKlcIzR6M9Pp3WOhpK0yJGWj5NLqKRDSbHd62UbDg_D8VHnPgPy3NHVsCq.V-slDbbdgQ6zajhY) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/ZHNvnTz-6Gh8_7HbLGTHJf0kv741AZz0gEvMFiMzPnXnh828ntK2TnXfoRCFd-OT.GCq-l4GJ_FyCH71M](https://us06web.zoom.us/rec/share/ZHNvnTz-6Gh8_7HbLGTHJf0kv741AZz0gEvMFiMzPnXnh828ntK2TnXfoRCFd-OT.GCq-l4GJ_FyCH71M) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/m8iqTE4VDNiwauTlDLx9yuFTB9hEtSsBpEUaVzgIGSR2wkFHWAsWxxW6szBTe7B8.18Gkrfbz_TPsM4_5](https://us06web.zoom.us/rec/share/m8iqTE4VDNiwauTlDLx9yuFTB9hEtSsBpEUaVzgIGSR2wkFHWAsWxxW6szBTe7B8.18Gkrfbz_TPsM4_5) - Recording link only. Origin: guide-06.txt.
- [us06web.zoom.us/rec/share/tGdJYwswNSKiI-Qw6A0WE5Ltsrymzjyv_lXBq3bvLCF2GWnHXgjtoqADEzyLPGQ.0gXmR2Y5XdULyYp-](https://us06web.zoom.us/rec/share/tGdJYwswNSKiI-Qw6A0WE5Ltsrymzjyv_lXBq3bvLCF2GWnHXgjtoqADEzyLPGQ.0gXmR2Y5XdULyYp-) - Recording link only. Origin: guide-06.txt.
- [www.bakom.admin.ch/bakom/de/home/geraete-anlagen/allgemeines/bitte-nicht-stoeren.html](https://www.bakom.admin.ch/bakom/de/home/geraete-anlagen/allgemeines/bitte-nicht-stoeren.html) - Example government content; not Skony gold data. Origin: uzh-slides PDF p.2, uzh-slides PDF p.3, uzh-slides PDF p.4.
- [www.bakom.admin.ch/bakom/de/home/geraete-anlagen/allgemeines/effizientere-notrufdienste.html](https://www.bakom.admin.ch/bakom/de/home/geraete-anlagen/allgemeines/effizientere-notrufdienste.html) - Example government content; not Skony gold data. Origin: uzh-slides PDF p.2, uzh-slides PDF p.3, uzh-slides PDF p.4.
- [www.bakom.admin.ch/bakom/de/home/geraete-anlagen/allgemeines/neue-wirtschaftsakteurinnen-im-bereich-des-e-commerce.html](https://www.bakom.admin.ch/bakom/de/home/geraete-anlagen/allgemeines/neue-wirtschaftsakteurinnen-im-bereich-des-e-commerce.html) - Example government content; not Skony gold data. Origin: uzh-slides PDF p.2, uzh-slides PDF p.3, uzh-slides PDF p.4.
- [www.bakom.admin.ch/bakom/en/homepage/equipments-and-installations/in-general/New-economic-operators-in-e-commerce.html](https://www.bakom.admin.ch/bakom/en/homepage/equipments-and-installations/in-general/New-economic-operators-in-e-commerce.html) - Example government content; not Skony gold data. Origin: uzh-slides PDF p.2, uzh-slides PDF p.3, uzh-slides PDF p.4.
- [www.bakom.admin.ch/bakom/en/homepage/equipments-and-installations/in-general/bitte-nicht-stoeren.html](https://www.bakom.admin.ch/bakom/en/homepage/equipments-and-installations/in-general/bitte-nicht-stoeren.html) - Example government content; not Skony gold data. Origin: uzh-slides PDF p.2, uzh-slides PDF p.3, uzh-slides PDF p.4.
- [www.ost.ch/en/research-and-consulting-services/computer-science/ifs-institute-for-software/ai-applications-and-deployment-lab](https://www.ost.ch/en/research-and-consulting-services/computer-science/ifs-institute-for-software/ai-applications-and-deployment-lab) - Linked reference / source snapshot; see coverage limits above. Origin: ost-slides PDF p.4.

## Appendix E. Supplied Devpost navigation and decorative links

These links were assessed for relevance and retained. Personal account routes,
platform help/social/footer links and branding assets supply no OpenParlData
technical requirement. Only event-specific public pages were used as rule evidence.

- [Devpost home](https://devpost.com/) - platform navigation.
- [Join/host/resources menu placeholder](https://hackapertus.devpost.com/rules#) - page fragment, not a distinct rules document.
- [Notifications](https://devpost.com/notifications) - personal account route; not inspected.
- [Supplied public profile](https://devpost.com/karyl1?ref_content=user-portfolio&ref_feature=portfolio&ref_medium=global-nav) - profile; not an eligibility ruling.
- [My projects](https://devpost.com/submit-to/30350-hack-apertus/manage/submissions) - authenticated route; not final organiser form.
- [Participants](https://hackapertus.devpost.com/participants) - requires sign-in in public retrieval.
- [Event resources](https://hackapertus.devpost.com/resources) - public source checked.
- [Gallery](https://hackapertus.devpost.com/project-gallery) - checked; unpublished.
- [Updates](https://hackapertus.devpost.com/updates) - checked; no additional public requirement retrieved.
- [Discussions](https://hackapertus.devpost.com/forum_topics) - checked; participant resource request is not organiser policy.
- [About](https://info.devpost.com/about) - platform footer; no challenge-specific evidence.
- [Contact](https://info.devpost.com/contact) - platform footer.
- [Help](https://help.devpost.com/) - platform footer.
- [Browse hackathons](https://devpost.com/hackathons) - platform navigation.
- [Explore projects](https://devpost.com/software) - general gallery; not this event ranking.
- [Host a hackathon](https://info.devpost.com/) - platform navigation.
- [Guides](https://info.devpost.com/guides) - general hosting/participation guidance.
- [Portfolio redirect](https://devpost.com/portfolio/redirect?page=projects) - personal route; not inspected.
- [User hackathons](https://devpost.com/portfolio/redirect?page=hackathons) - personal route; not inspected.
- [Settings](https://devpost.com/settings) - personal route; not inspected.
- [Community guidelines](https://info.devpost.com/legal/community-guidelines) - platform footer; separate from event conduct.
- [Security](https://info.devpost.com/legal/security) - platform footer.
- [California notice](https://info.devpost.com/legal/ca-notice) - platform footer.
- [Privacy](https://info.devpost.com/legal/privacy-policy) - platform footer.
- [Terms](https://info.devpost.com/legal/terms-of-service) - platform terms; not substituted for event terms.
- [Twitter](https://twitter.com/devpost) - social link; not inspected.
- [Devpost Discord](https://discord.com/invite/HP4BhW3hnp) - platform community, different from event Discord.
- [Facebook](https://www.facebook.com/devposthacks) - social link; not inspected.
- [LinkedIn](https://www.linkedin.com/company/devpost/) - social link; not inspected.
- [Devpost logo](https://assets.devpost.com/assets/reimagine2/devpost-logo-25d0005ec83e3b9ef6fce93235bb6d642d7c828f31758ebdb5b7ee87de7d45c3.svg) - decorative asset.
- [Profile image](https://d112y698adiu2z.cloudfront.net/photos/production/user_photos/005/233/989/datas/medium.jpg) - decorative asset.
- [Event banner](https://d112y698adiu2z.cloudfront.net/photos/production/challenge_photos/005/015/635/datas/full_width.png) - decorative asset.
- [GenAI Zurich prize event](https://www.genaizurich.ch/) - prize destination; not submission requirement.
- [Davos Tech Summit](https://davostechsummit.com/) - Track 2B prize destination, not Skony criterion.

## Appendix F. Original pasted source context

The following is the user-supplied text retained as source context. It includes
old notices, platform navigation and account snapshot details; these are not all
current rules. The assessment above resolves the relevant differences.

<details>
<summary>Resources and tools paste</summary>

# **Resources & Tools**

## 👉🏼 This page will be fully released on October 1st, 12:00.
We can't answer any questions in the meantime. Thanks for your understanding.

<aside>
💡

Our partners PHOENIQS, CSCS, Hugging Face, and Edit with Ava support you with several tools and credits. To apply for the resources, please use the **same email address** as your Devpost account. Otherwise, we can't provide access or codes.

</aside>

### **→ Resources**

#### **1) Inference support:**

!Devpost_logo (2).png.png)

**CSCS** supports all Hack teams by providing access via API.
**Update 6.10.26, 18:40 CEST**: Available keys have been distributed. We are no longer accepting new requests.

**2) Compute support:**

a) If you are a student at one of these academic partner institutions, contact your professor to get signed up: BFH, FHGR, FHNW, HSLU, OST, SUPSI, UZH, ZHAW
For the sign-up you'll need your institutional email address and an ID card or passport.

!Devpost_logo (3).png.png)

b) All others hackers may apply for support from our partner **Phoeniqs**.
**Update 4.10.26, 20:30 CEST**: We have received many great applications and are no longer accepting new ones.

### **3) Hugging Face:**

!HuggingFace.png

Get 10$ in credits for Inference Providers, Inference Endpoints, Jobs, Spaces, compute, storage, and more (subscription fees excluded).

👉🏼  Please sign-up here to get the code:
http://hackapertus.ch/online-hack/hugging-face

### **4) Edit with Ava:**

!EditwithAva.png

Edit with Ava supports your creative work with free credits for videos  Use it to create a compelling video about your prototype.

Go to and find all details how to access it: INFO PAGE

### **→ Mentorship**

!Mentors.png

Check out our amazing mentors who are happy to help you.
You can book a session online:
https://hackapertus.notion.site/mentors

### **→ Supporting Materials**

**Official Apertus website incl. documentation:**
https://www.apertus-ai.org/

#### **The model**

Apertus: Democratizing Open and Compliant LLMs
The primary source: architecture (xIELU activation, AdEMAMix optimizer), the legally-compliant training-data pipeline, the "Goldfish objective" against verbatim memorization, and benchmark numbers for both sizes.

Apertus v1 & v1.5 model collections
The actual checkpoints. v1 (8B/70B, base + instruct) and v1.5 (multimodal, longer context).

Data Transparency repository
Exactly what the model was trained on and how it was filtered. Useful if your project needs to reason about — or defend — data provenance.

---

#### **Examples & Demos**

Swiss Legal RAG Demo
A complete, minimal RAG app: Gradio front end, Apertus-8B via the HF Inference API, answering questions over the Swiss Federal Constitution and Data Protection Act in German, French, Italian, or English. No GPU, no vector database — deployable straight to a free HF Space. Copy this pattern for any "chat with our documents" project.

Apertus Translate
The core team's own experiments pushing Apertus on translation and other multilingual tasks, evaluated with both human raters and automatic metrics. A template for how to rigorously test any capability claim about the model, not only translation.

Apertus Probe
Trains linear probes on Apertus's internal activations to predict when it's about to hallucinate. A good starting point if your hackathon angle is interpretability rather than another chat app.

Case study: in-house translation for Canton of Ticino
A fine-tuned Apertus-8B now runs production translation for a Swiss cantonal government. A hint at where a public-sector framing for your project could go.

---

#### **Prompt Optimization**

A systematic Survey of Automatic Prompt Optimization Techiniques
A unifying framework and taxonomy across the field. Useful if you want to create the perfect prompt for your task.

#### **Fine-Tuning & Adaptation**

Apertus fine-tuning recipes
Pre-wired for this exact model: LoRA and full-parameter scripts, single-GPU 8B runs on a 40GB card, multi-node configs for 70B. Start here before anything generic.

PEFT & TRL libraries
The actual implementations you'll import: PEFT for LoRA/DoRA/prefix/prompt tuning, TRL's SFTTrainer for turning a dataset into a fine-tuned model in a few lines of code.

Alignment Handbook
The Alignment Handbook is a battle-tested SFT/DPO recipe template. Copy it instead of building a training pipeline from scratch.

#### 🏋🏻‍♂️ Overall Awesome Apertus overview

‣

#### **Contributions from FHNWbusiness**

- A Jupyter notebook for fine-tuning Apertus, tested on Kaggle and CSCS JupyterLab (Clariden):

**https://www.kaggle.com/code/andreasmartinch/sft-apertus-v1-5-8b-hack-apertus-template**

- A text-only version of Apertus 1.5 8B that can be loaded with the standard Transformers library:

**https://huggingface.co/andreasmartin/apertus-v1.5-8b-text**

- Experimental collection, including an embedding conversion of Apertus:

**https://huggingface.co/collections/andreasmartin/apertus**

</details>

<details>
<summary>Devpost event paste</summary>

Devpost
Join a hackathon
Host a hackathon
Resources

karyl1
Notifications
Loading...

Hack Apertus
Overview
My projects
Participants (898)
Resources
Rules
Project gallery
Updates
Discussions
Hack Apertus
Welcome to the first stage of «Hack Apertus», an open-source hackathon series to evaluate, align, and build on Apertus, Switzerland’s sovereign LLM.
Start project
Find teammates
Import from portfolio
Who can participate
Above legal age of majority in country of residence
All countries/territories, excluding standard exceptions
View full rules
1 more day to deadline
View schedule

Deadline

Oct 16, 2026 @ 3:00pm GMT+5
Grand Finals 2027
Public
€10,680 in cash	898 participants
aiLights Association
Education Machine Learning/AI Social Good
This Online hackathon is an invitation to spend just over two weeks building with Apertus, Switzerland's fully open LLM. From 1–16 October, builders everywhere gather online to push Apertus 1.5 further. And, you're invited.

If you care about open and trustworthy AI that anyone can use, this is your place.

You'll work with both the 8B and 70B models, backed by our partners CSCS and Phoeniqs, and experienced mentors alongside you. Everything you ship stays open and reusable.
The strongest projects advances to the Grand Finals in May 2027 in St. Gallen, Switzerland where you'll compete for the Main «Hack Apertus» Award.

🎯🎯 TRACKS & CHALLENGES
🎯 TRACK 1 - APERTUS READINESS is about improving the model.
1 A: Red-Teaming Apertus
1 B: Swiss Voices

🎯TRACK 2 - APERTUS ADOPTION is about showing what the model can do.
2 A: Academia Challenges
2 B: Own Project

👉🏼 All challenge descriptions can be found in our Getting Started Guide (1 OCT, 12:00).


📅  FIRST STEPS & TIMELINE
a) Join our Discord, our main comms channel
b) Find team mates on Discord if you don't work solo (1-5 allowed)
c) 1. OCT, 12:00 CEST: Tracks and Challenges are released
d) Book a session with one of our mentors
e) Check for Online sessions to support you
f) Work remotely on your solution
g) 16. OCT, 12:00 CEST, Final submission deadline
h) Our expert jury reviews all submissions and selects the winners until 23 OCT 2026

Note: This is the opening stage of a multi-month Hackathon journey. Over the following months, 6+ on-site hackathons across Switzerland follow. Join one Hack or all of them. Online and On-site run as separate phases, so you choose how far you go.
The Winners from each Hack will compete for 🏆 Main «Hack Apertus» Award on 14.05.2027 in St.Gallen.


👥 Who Should Participate?
Open to all, recommended for
AI/ML engineers, software developers, data scientists, researchers, and NLP practitioners, plus technical students (CS, data science, computational linguistics) and non-engineer domain experts (law, medicine, dialects, public sector).
Bring a team or find one on Discord.

👉🏼 Choose your track, find your team, and join a growing community advancing Apertus and showing where it can go next. Wherever you start, you'll help shape a sovereign, trustworthy foundation others can rely and build on.


New to Apertus? It's an open large language model built by teams from EPFL, ETH Zurich and CSCS and released fully in the open, trained across 1,811 languages. Free to use, free to build on.

Requirements
What to submit?
Submission deadline: 16 OCT 2026, 12:00 CEST
Please make sure you're in time, no extension possible.

The Tracks have different submission requirements which are published in the Getting started guide as of 1 OCT, 12:00 CEST.

All submissions are handled via our Website (not via Devpost):
https://hackapertus.ch/online-hack/submissions

Prizes
€10,680+ in prizes+ other prizes
Hack Apertus Online - Winner Red-Teaming
€2,670 in cash
1 winner
Cash Prize
(2,500 CHF) - paid in CHF
Qualifies to compete for the Main «Hack Apertus» Award (St.Gallen, 14.05.2027)
Hugging Face Credits (200 $)

Hack Apertus Online - 1st Runner-up Red-Teaming
1 winner
Hugging Face Credits (100 $)
A certificate + dedicated LinkedIn post

Hack Apertus Online - 2nd Runner-up Red-Teaming
1 winner
Hugging Face Credits (50 $)
A certificate + dedicated LinkedIn post

Hack Apertus Online - Winner Swiss Voices
€2,670 in cash
1 winner
Cash Prize (2,500 CHF) - paid in CHF
Qualifies to compete for the Main «Hack Apertus» Award (St.Gallen, 14.05.2027)
Hugging Face Credits (200 $)

Hack Apertus Online - 1st Runner-up Swiss Voices
1 winner
A Showcase spot at the Grand Finals (14.05.2027)
Hugging Face Credits (100 $)
A certificate + dedicated LinkedIn post

Hack Apertus Online - 2nd Runner-up Swiss Voices
1 winner
A Showcase spot at the Grand Finals (14.05.2027)
Hugging Face Credits (50 $)
A certificate + dedicated LinkedIn post

Hack Apertus Online - Winner Apertus Adoption: Academia
€2,670 in cash
1 winner
Cash Prize (2,500 CHF) - paid in CHF
Qualifies to compete for the Main «Hack Apertus» Award (St.Gallen, 14.05.2027)
Hugging Face Credits (200 $)

Hack Apertus Online - 1st Runner-up Apertus Adoption: Academia
1 winner
- 5 Summit passes for GenAI Zurich 2027 https://www.genaizurich.ch/
- A certificate + dedicated LinkedIn post
- Hugging Face Credits (100 $)

Hack Apertus Online - 2nd Runner-up Apertus Adoption: Academia
1 winner
A certificate + dedicated LinkedIn post
Hugging Face Credits (50 $)

Hack Apertus Online - Winner Apertus Adoption: Own project
€2,670 in cash
1 winner
- Cash Prize (2,500 CHF) - paid in CHF
- Qualifies to compete for the Main «Hack Apertus» Award (St.Gallen, 14.05.2027)
- Hugging Face Credits (200 $)
- ElevenLabs 3-month Scale Tier ($897 value/team member)

Hack Apertus Online - 1st Runner up Apertus Adoption: Own project
1 winner
Project Showcase at «Hack Apertus» Midway Event
→ 9.02.2027, Zurich, Novu Campus @ The Circle
→ Supported by Phoeniqs
→ Travel reimbursements for the team
- ElevenLabs 3-month Pro Tier ($297 value/team member)

Hack Apertus Online - 2nd Runner up Apertus Adoption: Own project
1 winner
- 5 Summit passes for Davos Tech Summit 2027
https://davostechsummit.com/
- ElevenLabs 3-month Pro Tier ($297 value/team member)

Devpost Achievements
Submitting to this hackathon could earn you:


First in-person hackathon

X Hackathons
 level 1

Hackathon Winner
 level 1

Generalist
Judges
Isabel Steiner
Isabel Steiner
President aiLights & Migros Online

Dr. Wiebke Hutiri
Dr. Wiebke Hutiri

Dr. Klaus L. Fuchs
Dr. Klaus L. Fuchs
Managing Director @ Rockstar

Prof. Dr. Andreas Martin
Prof. Dr. Andreas Martin
FHNW

Oleg Lavrovsky
Oleg Lavrovsky
Technical Community Manager SNAI

Prof. Dr. Siegfried Handschuh
Prof. Dr. Siegfried Handschuh
University of St.Gallen

Judging Criteria
Track 1A
Find details in challenge description
Track 1B
Find details in challenge description
Track 2A
Find details in challenge descriptions
Track 2B
- Purposeful use of AI - Technical rigour - Value, cost & scalability - Sovereign deployability - Implementation feasibility
To-dos
 Join the Discord

 Dismiss

Go Discord

 Dismiss

Read Terms & Conditions

 Dismiss

You're registered for this hackathon.

Unregister  Edit registration questions
Questions? Email the hackathon manager

Hackathon sponsors
Main Partners
Phoeniqs CSCS Innosuisse Kanton St.Gallen Kanton Bern Supertext BaselTech Wikimedia
Online Hack Partner
Livemap
Supporting Partners
Hugging Face ElevenLabs Edit with Ava
Academic Partners
BFH FHGR FHNW HSLU IDSIA OST University of St.Gallen University of Zurich ZHAW ZhdK
Founding organisation
aiLights
Co-Initiators
Artifact Swiss Engineering
This site is protected by reCAPTCHA and the Google Privacy Policy and Terms of Service apply.

Devpost
About
Careers
Contact
Help
Hackathons
Browse hackathons
Explore projects
Host a hackathon
Hackathon guides
Portfolio
Your projects
Your hackathons
Settings
Connect
 Twitter
 Discord
 Facebook
 LinkedIn
© 2026 Devpost, Inc. All rights reserved.
Community guidelines
Security
CA notice
Privacy policy
Terms of service

</details>

## Source reference definitions

[EVENT]: <https://hackapertus.devpost.com/>
[RULES]: <https://hackapertus.devpost.com/rules>
[FAQ]: <https://hackapertus.ch/faq#online-hackathon>
[GUIDE]: <https://hackapertus.notion.site/getting-started-guide-onlinehack>
[TRACK]: <https://github.com/HackApertus/project-template/blob/main/track_2a/README.md>
[TEMPLATE]: <https://github.com/HackApertus/project-template>
[TERMS]: <https://hackapertus.ch/terms-and-conditions>
[CONDUCT]: <https://hackapertus.ch/code-of-conduct>
[RESOURCES]: <https://hackapertus.notion.site/resources-tools>
[SUBMIT]: <https://hackapertus.ch/online-hack/submissions>
[OP]: <https://hackapertus.notion.site/track-2a-openparldata>
[DECK]: <https://hackapertus-document-extraction-26a562.gitlab.io/#/title-slide>
[OSTDATA]: <https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets>
[OSTSTART]: <https://gitlab.com/ifsoftware/hackapertus-starter>
[OSTAPI]: <https://hackapertus.notion.site/solution-api-guide-ef5b4fec112a834da43101ede56300f5>
[UZH]: <https://hackapertus.notion.site/track-2a-uzh>
[UZHDATA]: <https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD>
[UZHCODE]: <https://github.com/ZurichNLP/SwissGov-RSD>
[UZHQA]: <https://docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/edit?usp=sharing>
[ZHAWCODE]: <https://github.com/Fatemeh-MA/see-it-say-it-pick-it>
[FHGR]: <https://hackapertus.notion.site/track-2a-fhgr>
[APERTUS]: <https://www.apertus-ai.org/>
[MODEL8]: <https://huggingface.co/swiss-ai/Apertus-v1.5-8B>
[MODEL70]: <https://huggingface.co/swiss-ai/Apertus-v1.5-70B>
[PAPER]: <https://arxiv.org/abs/2509.14233>
[COLL1]: <https://huggingface.co/collections/swiss-ai/apertus-v1>
[COLL15]: <https://huggingface.co/collections/swiss-ai/apertus-v15>
[TRANSPARENCY]: <https://github.com/swiss-ai/apertus-data-transparency>
[LEGALDEMO]: <https://github.com/alexchilton/apertus_demo_hf>
[TRANSLATE]: <https://github.com/swiss-ai/apertus-translate>
[PROBES]: <https://github.com/swiss-ai/apertus-probes>
[TICINO]: <https://apertus-ai.org/articles/2026-03-ticino/>
[PROMPTSURVEY]: <https://arxiv.org/abs/2502.16923>
[RECIPES]: <https://github.com/swiss-ai/apertus-finetuning-recipes>
[PEFT]: <https://huggingface.co/docs/peft/index>
[TRL]: <https://huggingface.co/docs/trl/sft_trainer>
[ALIGN]: <https://github.com/huggingface/alignment-handbook>
[KAGGLE]: <https://www.kaggle.com/code/andreasmartinch/sft-apertus-v1-5-8b-hack-apertus-template>
[TEXT8]: <https://huggingface.co/andreasmartin/apertus-v1.5-8b-text>
[MARTIN]: <https://huggingface.co/collections/andreasmartin/apertus>
[AWESOME]: <https://github.com/rnckp/awesome-apertus>
[HFCREDITS]: <https://hackapertus.ch/online-hack/hugging-face>
[AVA]: <https://avlana.notion.site/Getting-Free-Credits-for-EditWithAva-3de3bdc93da0801d8934df4d9c8efd42>
[DISCORD]: <https://discord.gg/hack-apertus>
[MENTORS]: <https://hackapertus.notion.site/mentors>
[APIDOC]: <https://api.openparldata.ch/documentation>
[EXPORTS]: <https://files.openparldata.ch/exports/>
[PDFFILES]: <https://files.openparldata.ch/doc/>
[ADMIN]: <https://admin.openparldata.ch/>
[ECH]: <https://www.ech.ch/de/der-verein/fachgruppen/politische-geschaefte>
[BOOKLETS]: <https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978>
[P1]: <https://hackapertus.devpost.com/resources>
[P2]: <https://hackapertus.devpost.com/resources>
[P3]: <https://hackapertus.devpost.com/resources>
[P4]: <https://hackapertus.devpost.com/resources>
[P5]: <https://hackapertus.devpost.com/resources>
[P6]: <https://hackapertus.devpost.com/resources>
[P7]: <https://hackapertus.devpost.com/resources>
