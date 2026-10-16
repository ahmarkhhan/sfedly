# 09 — Ethics, Legal & Compliance

> Historical design specification. The [current project direction](16-project-direction.md)
> and [delivery backlog](18-delivery-backlog.md) supersede conflicting scope,
> rubric, schema, sample counts, commands and deployment assumptions below.
> Features here are proposals unless confirmed in the
> [implementation status](../track_2a/docs/BUILD_STATUS.md). Source location
> does not establish semantic correctness or human approval.

## Conservative extraction (the challenge's ethics brief, adopted verbatim as policy)

- **Minimise hallucinations, keep content traceable to source.** → Enforced mechanically by the verbatim guard (SK-B3): ungrounded values cannot survive the pipeline.
- **Do not introduce, omit or substantively alter source information.** → Extracted values are verbatim substrings; normalisation (dates, case) is documented and the original string is preserved in `provenance.quote`.
- **Stay faithful to original wording and meaning — the PDF is always authoritative.** → Every UI path and every export links back to the document; extracted data is a view over the PDF, never a replacement.
- **Clearly distinguish extracted vs generated/inferred content.** → `origin` on every field (`extracted` / `inferred` / `manual`), visible in UI and exports. Translations and answer text are always labelled generated.
- **Where extraction isn't reliable: say so, don't guess.** → First-class abstention with reason codes; refusals in the answer API; abstention metrics published, not hidden.

## Data protection & legal

- Corpus contains only material already published by the parliaments themselves (per OpenParlData); no personal data beyond what is public in official documents.
- No scraping of new sources at runtime; the demo corpus is the officially provided one.
- Outputs openly accessible and reusable, per the challenge's legal section.

## Open source & licensing

- Event T&C §6: everything built is open source. Skony intends **Apache-2.0** (patent grant, compatible with public-sector reuse).
- All dependencies are OSS; a `NOTICE` file lists model and data attributions (Apertus by swiss-ai/ETH-EPFL-CSCS; OpenParlData corpus CC-licensed per source terms).
- Documentation (this set) ships in `docs/` inside the submission repo — open by default, auditable by design.

## Sovereignty

- **Apertus only.** No call to any external commercial LLM exists anywhere in the dependency tree (checked in CI, SK-G2).
- **Runs on Swiss infrastructure**: self-hosted 8B on a VPS, or CSCS/Phoeniqs endpoints — no data leaves the jurisdiction.
- **No vendor lock-in**: PostgreSQL, plain JSON, documented schema; everything exportable and re-hostable.
- Auditable end to end: prompt versions, model versions, and verification rules are pinned data — any published number can be re-derived (`make eval`).

## Known limitations (declared up front — see technical report for the living list)

- Scanned/handwritten pages degrade extraction; Skony abstains rather than guesses, which trades coverage for precision.
- Schema generalisation across all 90 parliaments is the open research question — Skony measures it on 3–5 bodies and reports honestly, including where the schema breaks.
- 8B quality on FR/IT trails DE; per-language metrics make the gap visible instead of averaging it away.
