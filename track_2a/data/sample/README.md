# Public engineering demonstration

This directory contains an **authored synthetic practice document**. Its people,
parliament and affair are fictional. Suggested fields were authored to exercise
the evidence/review workflow; **they are not Apertus output or human gold**.

The default recorded demonstration checks the PDF and candidate hashes, applies
the real evidence verifier, and imports the result as unreviewed. Confirming a
field demonstrates review persistence; it does not create evaluation gold.

All fixture content was created for Skony. Dataset licence:
[CDLA-Permissive-2.0](https://cdla.dev/permissive-2-0/).
The generating program is Apache-2.0 with the application code. These rights do
not extend to the separate private Nidau pilot, whose redistribution basis
remains unverified.

The checked-in PDF is sufficient to run. To deliberately rebuild it with the
pinned dependencies, run `python scripts/build_demo_fixture.py`. This updates
the manifest; a changed PDF digest represents a new source version.

Real parliamentary samples, recorded Apertus responses and a human-reviewed
DE/FR evaluation corpus are still required for the research contribution.
