# Evaluation implementation and verification

**16 October 2026 — Asia/Karachi**

The missing B1–B7 evaluation tooling is implemented. The final suite passed
**197 Python tests and 4 interface tests**. The initial suite passed 133 Python
tests; 64 new regressions cover the added evaluation behavior.

| Area | Verified behavior |
|---|---|
| Corpus | Retains all 45 selected rows, verifies 44 PDFs and preserves the failed source. Human language/role/membership review gates acquisition. |
| Relationships | Freezes all eligible candidate pairs, supports independent annotation packets and adjudication, and scores the three relation kinds separately. |
| Existing-data comparison | Saves full API samples and reproducible queries; rejects metadata-only novelty claims. |
| Human review | Checks competence, calibration, exposure, independent coverage and non-circular comparisons. |
| Schema findings | Keeps expressivity, mapping and extraction recovery separate; requires cited counterexamples for conditional or negative findings. |
| Experiments | Freezes output capacities on development cases; records failures, truncation and usage; reuses exact B1 responses for B2 and verifies zero-network replay. |

The real-corpus cohort, metadata baseline, feasibility matrix and readiness reports
were reconstructed from their saved artifacts with identical results. The CLI
round trip also matched and refused to overwrite existing evidence. Published
schemas match the code, and the independently audited plan's hash is unchanged.

No new human annotations or live model calls were made. **Research evidence is
not yet complete:** competent intake review, independent blind gold, substantive
source-backed findings and real benchmark results remain required. Existing
model-assisted reviews are not silently promoted into blind gold.

The prepared live capacity probe contains text from two saved development PDFs:
Bern `351_908378.pdf` and Geneva `6621_927024.pdf`. It is bounded to four calls to
`https://api.inference.cscs.ch/v1`. Automatic approval review rejected that run
because explicit approval did not cover transmitting those PDFs to that external
destination. The probe remains unrun.

Local evidence:

- Full Python test log (local evidence, excluded from the public repository)
- Offline reconstruction proof (local evidence, excluded from the public repository)
- Research gate status (local evidence, excluded from the public repository)
- Prepared model inputs (local evidence, excluded from the public repository)
- [Implementation and operating guide](EVALUATION_IMPLEMENTATION.md)

These local output artifacts are ignored working evidence, not a public
submission package or a certificate of extraction accuracy.
