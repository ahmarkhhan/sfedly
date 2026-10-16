# Skony: official-instructions gap audit

Reviewed on **16 October 2026, Asia/Karachi** against the supplied OpenParlData brief, the live challenge page, the official GitHub template, the live OpenParlData submission form, the event terms, the working implementation, and the public submission repository.

**Assessment:** Skony has a working extraction and review foundation. The largest remaining gap is the research evidence requested by the challenge: a checked multilingual and multi-level sample, measured extraction quality, substantive schema findings, and an answered cross-parliamentary question. The working implementation is also ahead of the source published for judges. Matching the submission requirements is controllable; a guaranteed 100/100 is not. The supplied judging criteria have no numerical point allocation.

**What judges prioritize.** The challenge's primary criterion is insight into whether a common representation is feasible, followed by breadth and applicability across parliaments, document types, and languages. It explicitly accepts a well-supported partial or negative conclusion. A review interface supports this investigation, but the provider already has a workbench. Additional interface features have lower priority than finishing the schema and evidence. [Official challenge](https://hackapertus.notion.site/track-2a-openparldata).

**Verified starting point**

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Working source: **212 Python tests passed**, plus **4 interface tests passed**, during this audit | Existing engineering behavior passes its tests | Real extraction accuracy, human agreement, or broad applicability |
| Saved real DE/FR pipeline proof: two Apertus 1.5 70B calls; identical zero-call replay | Real inference, cache reuse and retained failed-source accounting | A representative or human-scored benchmark |
| Private selection: 45 source rows, 44 pinned PDFs, one failed fetch; five body labels | A useful starting collection exists | Checked language, government level, document role or evaluation membership |
| Prepared cohort: all 45 units have unknown level, no intake review and unassigned split | The research preflight preserves missing evidence honestly | A completed development/test study |
| Saved readiness report: six of seven evidence gates open | Evaluation tooling exposes the gaps | Completed research results |
| Feasibility matrix: all current concept/body findings untested | A structure for reporting findings exists | A conclusion about schema feasibility |
| Novelty report: no findings; information-gain gate false | Metadata comparison tooling exists | The required cross-parliamentary answer |
| Public GitHub run #10: container verification step passed; report-branch publication failed | The earlier published source passed its container verification step | A green overall workflow or container verification of the newer working source |

The first test attempt encountered Windows sandbox restrictions on sockets and temporary-file replacement. The same existing Python suite passed with the required local access. No parliamentary document was transmitted to a model during this audit. Test log: `../track_2a/output/official-instructions-audit-tests.log`.

**Official requirements mapped to the project**

| Requirement | Current position | Change needed / evidence of completion |
|---|---|---|
| Public reference implementation | Public `ahmarkhhan/sfedly` exists, with the selected track directory, converter and prompt | Publish the selected final implementation and its supporting samples/results; verify from that exact commit |
| Apertus-driven conversion | Real saved 1.5 70B calls exist; configurable client and conservative prompts work | Record exact requested/reported model identity, provider, prompt/schema versions, generation settings and raw outputs for the evaluated run |
| Versioned, documented common representation | v0.1 raw fields and v0.2 candidate/review contracts exist | Identify one canonical affair export; document core fields, extension points, cardinalities, null/absence/unsupported meanings and complete examples |
| Four controlled vocabularies | Four draft vocabularies and deterministic mapping exist in the working copy | Correct questionable equivalences; scope mappings to body/language where necessary; publish them and exercise their use on real reviewed examples |
| Submitters, co-signatories, addressed body, Q/A pairings, dates, history, decisions, related affairs | Eight core fields plus v0.2 actor/event/relation proposals provide partial coverage | Demonstrate explicit roles, scoped affairs and separately linked documents; complete or clearly bound each structural capability |
| Images, tables and annexes | Original PDFs and region citations are retained; no full structured-content extraction path was demonstrated | Preserve ordered content blocks, table/cell structure or referenced assets and annex relationships; demonstrate at least one difficult real example. Flag unsupported cases explicitly |
| Page provenance and text span where possible | Strong existing support: immutable text, page/quote/span checks and visual evidence | Show that role assignment and full paragraph boundaries are correct on gold; distinguish source location from semantic correctness |
| Multilingual, multi-level evaluation against manual gold | Collection and scoring tools exist, but checked gold/split/results remain incomplete | Finish a bounded real study with checked strata, source-based human labels, held-out evaluation and retained failures |
| At least one useful cross-parliamentary answer | Offline comparison and metadata-novelty tools exist; saved substantive findings are empty | Publish the question, baseline, reviewed answer, reproducible query, limitations and citations to all answer claims |
| Well-founded feasibility conclusion | Matrix generator exists, but its findings are untested | Fill it with source-backed positive/conditional/negative findings and explain fundamental differences separately from model errors |
| Docker execution using `make run` on clean checkout | Packaging exists; public run's container step passed for older code | Verify the final submitted commit; fix the separate report-publication failure; document replay versus live behavior |
| `data/` at most 100 MB | Current public checkout is about 26 KB; working data is about 22 MB | Recheck after adding final examples/gold; exclude secrets and unrelated local folders |
| Report and complete submission | Existing local report PDFs are two pages, within the limit, but content is stale | Rewrite with actual final findings and metrics, and submit the final PDF and public repo through the official form |
| Open, reusable outputs and item-level dataset licences | Apache-2.0 code licence exists; sample data has a dataset licence | Make documentation/data notices consistent, retain third-party attribution and state publication basis per included item |

The template requires keeping `track_2a/`, Docker execution via `make run`, the three `LLM_*` settings and the data cap. It does not mandate a particular application framework. [Project template](https://github.com/HackApertus/project-template), [Track 2A instructions](https://github.com/HackApertus/project-template/blob/main/track_2a/README.md).

**Fix 1: make the submitted repository match the work**

The active working source is `D:/development/Skony/track_2a`. The separate Git checkout linked to the public submission is `D:/development/Skony/sfedly`.

Both the local submission checkout and the public source listing lack these newer working modules: `evaluation_api.py`, `evaluation_common.py`, `evaluation_insights.py`, `evaluation_protocol.py`, `evaluation_status.py`, `experiments.py`, `relations.py`, `study.py`, and `vocab.py`. The controlled-vocabulary directory is also absent from the inspected public source. Its README still claims 82 tests. Publishing the current documentation alone would describe capabilities that judges cannot reproduce.

Reconcile code, tests, vocabulary files, documentation and redistributable evidence into the submission repository. Preserve its Git history and local report changes. Do not copy the outer workspace wholesale: it also contains unrelated projects, research downloads, private corpus/cache files and runtime state. Verify the final clean checkout and identify its commit in the report.

Public source observed: [source directory](https://github.com/ahmarkhhan/sfedly/tree/main/track_2a/src/skony). Public HEAD observed during this audit: `fe15344bc3704b61f01bdc7c3113301ba9130990`; the local submission checkout was at `e70804e`.

**Fix 2: turn evaluation tooling into measured evidence**

Choose a study small enough to finish competently. A strong prototype target would be roughly **12–20 affairs / 24–40 documents**, spanning several bodies, at least DE and FR, and at least two government levels. Add Italian and a federal example when competent review and suitable sources are available. These are recommendations, not official quotas; the brief sets no minimum sample count. Smaller, honestly bounded findings are better supported than claims based on unreviewed downloads.

Include actual request/response pairs, decisions, varied affair types, multi-page text, scans with and without usable text, and at least one table/annex case. Check each unit's language, level, role and affair membership from the source. Count acquisition, parser, model and schema failures in the reported coverage.

Freeze development and held-out test groups by affair, including linked documents, duplicates and translations in the same group. Use source-first human gold that is independent of the scored predictions. Existing model-assisted review remains useful, but its exposure must be disclosed. A second competent reviewer on a subset and recorded disagreements strengthen the result; the official brief does not prescribe a specific double-review percentage.

Use the already implemented experiment tools to compare a simple Apertus baseline, schema-constrained Apertus, and the same constrained outputs after evidence checks. Tune capacities/prompts only on development cases. Report:

- field precision, recall and F1, with the matching policy stated;
- full question/answer completeness and separate Q/A relation scores;
- page/span correctness, unsupported predictions, abstention and coverage;
- JSON/schema validity, failed/truncated inputs, actual usage and latency;
- results by body, language, government level and difficult document type, with sample counts.

A higher precision after rejecting many predictions must be shown alongside the coverage loss. A correct quote can still be the wrong person's name or an executive recommendation mislabelled as a parliamentary decision.

Publish enough frozen inputs, gold, outputs and evaluation commands for a judge to reproduce the numbers. For material that cannot be redistributed, provide a permissible source retrieval recipe with original IDs, URLs and hashes, and clearly state any remaining access limitation. Ignored private output is not a public submission artifact.

**Fix 3: answer the main research question**

Populate the existing feasibility matrix for each tested body and concept. Keep three questions separate:

1. Can the schema represent the source faithfully?
2. Can its local concept be harmonized with another parliament without changing its meaning?
3. Can this converter recover it reliably?

For every conditional or negative finding, cite a real counterexample. For positive findings, supply representative checked examples and counts. Explain which fields form a useful common core, which need local extensions, and which should remain incomparable. Extraction failure alone is not proof that a shared representation is impossible.

**Fix 4: finish one cross-parliamentary result**

The prepared question is a sensible starting point: what conditions accompany executive responses, and what linked parliamentary decisions follow them? Narrow it to the sampled affairs and at least two bodies. Choose another question if this sample lacks the relevant documents.

Produce a table with body, affair ID, exact response condition/reason, actual decision, uncertainty and page/span references. Establish what the existing API metadata and extracted text already provide, then show the added reliability or structure supplied by PDF extraction. An already available title/type/date comparison does not, by itself, demonstrate this contribution. Reproduce the answer with an offline query over reviewed records; no chatbot is required.

**Fix 5: correct the representation and vocabulary before claiming comparability**

The primary live review workflow still uses v0.1: one page/quote per field and a 50,000-character prompt limit. v0.2 supports multi-segment proposals and typed relations; its HTTP route validates imported recordings. The richer contract therefore needs an end-to-end real example and a clear judge entry point. Avoid making the eight-field v0.1 output stand in for every promised affair semantic.

Define a canonical affair record with stable body-scoped identity, source documents and their roles, actors with role evidence, ordered question/response items, procedural events and decisions, related-affair links, and structural content/annex references. Keep original labels and dates alongside explicitly derived normalized values and mapping versions. Preserve separate meanings for missing, unreadable, ambiguous, outside scope and unreviewed information. The existing v0.2 components can support this work; a fresh redesign is unnecessary.

Two concrete corrections are required in the current drafts:

- `src/skony/vocab/affair_types.yaml:59` includes `Standesinitiative` as an alias of Motion. `map_label()` returns `exact_in_scope` for this global alias without checking the body. The federal Parliament documents cantonal initiatives and motions as distinct instruments with different procedures. Remove this exact equivalence; represent the distinction or use an explicitly justified broader/unmapped relation. Review the other global question-type aliases as well. [Parliamentary procedures](https://www.parlament.ch/de/%C3%BCber-das-parlament/parlamentsportraet/beratungsgegenstaende-und-parlamentarische-verfahren/parlamentarische-initiativen-standesinitiativen-vorstoesse).
- `docs/VOCABULARY.md:70` describes eCH-0039 as a four-type parliamentary-affair standard. The official standard is a general dossier/document exchange interface. The political-affairs group lists separate standards under development, including eCH-0295. Remove unsupported A/B/C mappings and check every alignment against the actual standard version and concept. Placeholder `/akn/.../` strings should be labelled illustrative alignments, not interoperable identifiers. [eCH-0039](https://www.ech.ch/de/ech/ech-0039/3.0), [Political-affairs standards](https://www.ech.ch/de/der-verein/fachgruppen/politische-geschaefte).

For tables/images/annexes, retaining an original PDF is valuable, but does not itself provide a structured representation. Demonstrate ordered content blocks and explicit references, retaining budget units/headers and source regions where applicable. If extraction remains unsupported, show a real failure and bound the claim. A partial schema conclusion is allowed; claiming unimplemented content handling is not justified.

**Fix 6: make execution evidence and documentation agree**

The latest inspected public workflow is marked failed. Its specific container build/test/preview/persistence step is marked passed. The report-branch publication step failed with exit code 128; detailed logs require sign-in, so the precise Git error was not established. [Run #10](https://github.com/ahmarkhhan/sfedly/actions/runs/38821568786/job/116719110418).

Fix or remove the optional branch-publication step while retaining downloadable verification artifacts. Do not treat that publication failure as proof of a failed container. Rerun verification on the final synchronized commit, because the passing step covers the earlier public implementation.

Rewrite the report and READMEs around the final state. They currently contain conflicting 82/132/197 test counts, say vocabulary mapping is unimplemented despite the new working code, and describe container execution as unverified despite the passed public step. The correct audit-time working count is 212 Python tests plus four interface tests, and it must not be advertised as the public source's count until that source is synchronized and tested.

Use the official report's summary, architecture, Apertus setup, data, evaluation, limitations, reproducibility and next-steps structure. Include team, demo reference, exact commit and actual measured results. The existing two-page PDF meets the page cap, but needs substantive updating. [Report template](https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md).

The live OpenParlData submission form requires a **PDF of at most six pages**, repository URL including converter/prompts/validator/README samples, and completed participant/team/model fields. Deadline shown: **16 October 2026, 12:00 CEST = 15:00 Asia/Karachi**, with no extensions. Submit through the organizer website. [Official form](https://hackapertus.ch/online-hack/submissions).

The terms specify Apache-2.0 for code/weights, CC-BY-4.0 for non-code material and CDLA-Permissive-2.0 for submitted datasets, subject to stated exceptions and third-party rights. The public root README describes the synthetic fixture as CC-BY while its manifest/README specify CDLA; reconcile the notices. Identify the licence of each included source item rather than assuming public accessibility grants every redistribution right. [Event terms, section 6](https://hackapertus.ch/terms-and-conditions).

**Recommended completion order**

1. Resolve which source tree is being submitted; preserve ongoing changes and assemble the final code in that repository.
2. Complete source intake and human gold for a bounded, diverse study; reserve held-out cases.
3. Correct vocabulary equivalences and exercise the canonical schema on the selected real affairs.
4. Run the prepared comparison and publish metrics, failure accounting and substantive feasibility findings.
5. Publish one reviewed cross-parliamentary answer with its baseline and source citations.
6. Verify the final container/clean checkout, make CI reporting succeed, update the report/README and submit before the deadline.

If competent human review is available now, start it immediately while packaging and documentation are finished. Do not spend the remaining time building more evaluation scaffolding: the essential tools already exist. A large-scale run over the full 300,000-affair corpus, fine-tuning, a new front end, a chatbot and self-hosting the 70B model are not stated submission requirements. Preserve caching, bounded calls and resume/failure accounting, and report scale estimates only with measured assumptions.

**A convincing judge demonstration**

In a short walkthrough, show a real source page, the corresponding canonical affair record, a correct cross-document Q/A or decision link, the reviewed cross-parliament answer, and one difficult case where the system abstains. End with the measured results and source-backed feasibility conclusion. Clearly label live inference, recorded Apertus output, synthetic practice data and human-reviewed gold throughout.

This audit added recommendations and a test log only. It did not change application code, publish a commit, run new inference, fabricate human annotations, or submit the project.
