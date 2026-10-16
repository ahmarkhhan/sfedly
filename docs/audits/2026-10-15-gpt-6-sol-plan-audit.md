# Independent evaluation audit — GPT-6-sol

**Date:** 15 October 2026, Asia/Karachi.
**Auditor:** GPT-6-sol, high reasoning, isolated initial context.
**Reviewed document:** docs/19-prototype-excellence-plan.md, revision 1.0.
**Verified SHA-256:** e10ea79787520d8a405587fe745fe37e43567114ae7ffa62635809073698f09b.
**Scope:** read-only planning audit explicitly requested by the user.
**Original verdict:** conditional.

## Auditor's original report

The plan is strong enough to guide implementation, but the following design decisions should be fixed before freezing the study.

| ID | Severity | Plan section | Issue and minimum correction |
|---|---|---|---|
| B1 | High | §9, corpus target and split | The proposed 12 request/response affairs are not supported by the current candidate pool. The 45-row manifest has 18 request, 5 response, and 22 unpaired metadata labels; only one body/affair key occurs more than once. Make acquisition and human role/link verification a blocking feasibility gate before committing to 48 documents, 24 affairs, or paired-affair metrics. Predeclare the smaller study and its claims if acquisition fails. |
| B2 | High | §§9–10, gold and relations | Gold v0.2 makes scoped relations optional (“where evaluated”), while affair membership, Q/A alignment, and decision linkage are central claims. Require adjudicated labels for each relation actually claimed on the held-out affairs, including explicit negative/unknown cases and a fixed candidate-pair universe. Define link scoring separately for affair–document, question–answer, and response–decision relations. |
| B3 | High | §§8, 12, cross-parliamentary answer | The proposed procedural fallback may be answerable from OpenParlData's existing structured metadata. The brief requires a question that cannot currently be answered reliably. Before selecting the demonstration, document what the existing API/metadata can answer, then show the additional PDF-grounded facts, corrected links, or changed conclusion supplied by Skony. If the fallback adds no demonstrable information, choose another bounded question. |
| B4 | High | §§9–10, human review and B3 | B3's final reviewed snapshot could be the same annotations used as gold, making apparent post-review accuracy circular. Use a separate assisted-review workflow and reviewers for B3, compared with frozen blind gold, or report B3 only as workflow/output evidence without a quality-uplift estimate. Preserve reviewer overlap and exposure records. |
| B5 | Medium | §9, independent annotation | At roughly 18 held-out affairs, 25% double review covers only about five affairs, fewer than the six target bodies. Set a minimum independent-review allocation across every body and both languages, with hard cases and relation labels included; define reviewer language/procedural competence and calibration before annotation. Disclose singly annotated strata and avoid precision claims that exceed this support. |
| B6 | Medium | §§5, 10, feasibility matrix | The matrix mixes schema expressivity with extraction errors. A failed OCR or missed answer does not show that the common schema cannot represent it. Give each concept/body cell separate judgments for source-supported representability, mapping loss or semantic collision, and pipeline recovery; require cited counterexamples for conditional or negative schema conclusions. |
| B7 | Medium | §10, B0/B1/B2 | B0 produces simpler JSON while B1 must emit evidence under nominally matched generation budgets. A shared output limit could truncate B1 disproportionately. Predefine enough output capacity for each contract, report token use and truncation, and compare B0/B1 on the same projected field values. Score provenance and schema-contract compliance separately; retain B2's byte-identical B1 input. |

The plan's strongest features are its honest scope limits, scoped absence states, preserved local terminology, immutable provenance, failure accounting, and explicit separation of B2 filtering from generation. It correctly treats the existing zero-call replay proof as engineering evidence, not an accuracy benchmark. The archived official brief rewards insight and breadth and accepts convincing partial or negative findings; the plan does not misstate the user's numerical rubric as official.

This audit certifies neither implementation nor a score. Corpus suitability, reviewer competence and independence, gold correctness, measured B0/B1/B2 behavior, and the usefulness of the final cross-parliamentary answer require actual documents, human work, and frozen runs.

## Plan author's disposition

All seven findings were accepted and addressed in revision 1.1. The specific changes are mapped in [the plan's audit ledger](../19-prototype-excellence-plan.md#16-independent-llm-audits-and-incorporated-corrections). The independently authored original report above is distinct from this disposition. A closure check against the frozen revised document is recorded below when returned by the auditor.

## Auditor's closure check

**Reviewed revision:** 1.1.
**Verified SHA-256:** 32249cd419b72ec6dd181ff2a4e046c5b2baa7c587ac859996244b69b19aa86e.
**Revised verdict:** ready for implementation.

The auditor checked the revised plan rather than its disposition ledger.

| Finding | Status | Evidence in revision 1.1 |
|---|---|---|
| B1 | Closed | §9 makes verified roles and enough genuine pairs a blocking acquisition gate, with a smaller-study fallback and restricted claims. |
| B2 | Closed | §9 requires gold for every claimed held-out relation, freezes candidate-pair universes, and records positive, negative, and unknown labels. |
| B3 | Closed | §8 requires a saved existing-API/metadata baseline and demonstrated PDF-derived information before either question closes the gate. |
| B4 | Closed | §10 removes default B3 accuracy-uplift claims and requires separate assisted review against blind gold for such a comparison. |
| B5 | Closed | §9 raises independent review to at least one affair per tested body, with language competence, calibration, hard cases, and disclosed single annotation. |
| B6 | Closed | §10 separates schema expressivity, harmonization, and pipeline recovery in the feasibility matrix, with cited counterexamples. |
| B7 | Closed | §10 sets output capacity on development cases, reports truncation and usage, and compares B0/B1 on the same projected fields. |

The revised plan also fixes the direct-count F1 edge case and groups shared multi-affair artifacts into connected split components. **No material blocker remains in the plan text.** The acquisition, human gold, and measured results remain future evidence gates; this is a plan-only verdict.
