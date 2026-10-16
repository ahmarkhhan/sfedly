# Controlled vocabularies (v0.1-draft)

Versioned controlled vocabularies for the four classification dimensions of a
parliamentary affair. Raw extracted values are **never overwritten**: a
vocabulary mapping is a separate, replayable object (`skony.vocab.Mapping`,
renderable as a `MappingRule` from `review_contracts.py`) that points from the
preserved raw label to a stable term ID and records which deterministic rule
fired.

| Vocabulary | File | Terms | Scope |
|---|---|---|---|
| Affair types | `src/skony/vocab/affair_types.yaml` | 10 | What kind of affair (Interpellation, Motion, Postulat, Petition, government report, …) |
| Actor roles | `src/skony/vocab/actor_roles.yaml` | 8 | Who acts (submitter, co-signatory, committee, group, government, respondent, chancellor, petitioner) |
| Procedural states | `src/skony/vocab/procedural_states.yaml` | 9 | Where the affair is in its lifecycle (submitted → referred → answered/debated/decided → closed/withdrawn/expired) |
| Decision outcomes | `src/skony/vocab/decision_outcomes.yaml` | 6 | How it ended when a decision is printed (adopted, rejected, partially adopted, taken note, referred back, none recorded) |

Status **draft**: IDs are stable once published; prefLabels and alias lists are
expected to grow as the gold set is annotated. Anything that does not match an
exact normalised alias maps to `unmapped` — an explicit, reviewable outcome,
never a guess. There is deliberately **no fuzzy/substring matching** in v1:
"conservative extraction, say so when unreliable" applies to vocabulary
assignment too.

## Design rules

1. **Raw first.** `affair_type_raw`, `submitter_raw`, `decision_raw` stay
   byte-exact quotes with page/span provenance. Mapping happens *after*
   extraction and review, as its own versioned layer (`vocabulary_version` is
   recorded on every mapping).
2. **Hierarchy via `broader`.** E.g. `at.interpellation` and
   `at.simple-question` are both `broader: at.question`. A body that prints
   only "Vorstoss" maps to the generic parent; the distinction is not
   invented. Aggregation queries choose which relation types they accept via
   `permitted_mapping_relations` (already in `ComparisonSpec`).
3. **Small enough for a municipality.** The minimal useful set is 4 affair
   types (question, postulate, motion, government report), 3 roles
   (submitter, government, respondent), 3 states (submitted, answered,
   closed), 3 outcomes (adopted, rejected, taken-note). National parliaments
   use the same IDs with more aliases — the vocabulary does not fork per
   level.
4. **Multilingual by construction.** Each term carries `pref` labels in
   en/de/fr; aliases are per-language surface forms as printed by the bodies.
   Normalisation (NFKD, diacritic-strip, casefold, punctuation-collapse) makes
   "Pris acte" ≡ "pris-acte" ≡ "PRIS ACTE".

## Mapping to existing standards

The alignment is *naming/semantic alignment*, not a claim of full conformance.
Targets chosen for actual Swiss parliamentary-data practice:

| skony concept | Akoma Ntoso 3.0 | Popolo 1.0 | OParl 1.1 | Parla-CLARIN |
|---|---|---|---|---|
| affair (whole record) | `documentType` + `FRBRWork` | `Motion` | `Paper` + `Consultation` | `term:AgendaItem` |
| at.interpellation / at.simple-question | `/akn/.../question` family | `Motion` with classification | `paperType: Interpellation/Anfrage` | question speech event |
| at.motion / at.postulate | `/akn/.../motion` | `Motion` | `paperType: Motion/Postulat` | motion event |
| at.government-report | `/akn/.../report` | — | `paperType: Beschlussvorlage` | report reference |
| role.submitter | `TLCPerson` referenced by `meta` | `Person` + `Membership` | `Person` | speaker link |
| role.government / role.committee | `TLCOrganization` | `Organization` | `Organization`/`Body` | body reference |
| procedural states | lifecycle `eventRef`s | `Motion` status fields | `Consultation` role/status | sitting/event structure |
| decision outcomes | `decision` in `judgment`/`conclusions` | `VoteEvent.result` | `resolutionText` | vote annotation |
| provenance (page+span) | `mod`/`quotedText` anchors | — | — | `annotation` spans |

Docling is a *document-format* layer (lossless PDF→structured JSON with table
and layout cells), not an affair ontology: it is the natural future carrier
for multi-page table/budget content (each Docling cell keeps its own bbox
provenance, matching our page+span model). Where the current pipeline extracts
page text only, annexes/tables are flagged `textless`/unmapped rather than
silently dropped.

**eCH-0039** standardizes exchange of electronic dossiers and documents;
it is not used here as an affair-type taxonomy. The unsupported A/B/C
type mappings were removed in v0.1.1-draft.
Source: [official eCH-0039 catalogue](https://www.ech.ch/de/node/455091).

`Standesinitiative` is no longer a Motion alias. It remains explicitly
unmapped until a separate reviewed vocabulary term is introduced.
Source: [Swiss Parliament: initiatives and interventions](https://www.parlament.ch/de/%C3%BCber-das-parlament/Seiten/parlamentarische-initiativen-standesinitiativen-und-vorstoesse.aspx).

## Deterministic mapping rules (v1)

| Rule | Fires when | Result |
|---|---|---|
| `empty` | raw label is null/blank | `unmapped` |
| `alias-exact` | normalised label equals a prefLabel or alias | `exact_in_scope` → term |
| `no-alias` | anything else | `unmapped` (queued for human review) |

Human reviewers extend coverage by adding aliases to the YAML — every alias
addition is a vocabulary version bump, so past mappings stay replayable and
re-mappable. Run the summary with `python -m skony.vocab`.
