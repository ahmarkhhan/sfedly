# Skony — parliamentary data with proof

**Current direction:** an Apertus 1.5 converter for comparable parliamentary
request/answer records, preserving source evidence and measuring where the
representation works or fails across bodies and languages.

**Now usable for research:** the [affairs explorer](track_2a/docs/EXPLORER.md)
at `/explore` searches original PDF text, filters by parliament/language/topic,
opens source-linked dossiers with requests, answers, dated events and signatories,
and exports cited JSON/CSV briefs. It works on imported documents before review;
unreviewed suggestions and practice data are labelled explicitly.

- [Public data, synchronization and secret handling](track_2a/docs/PUBLICATION.md)
- [Authoritative project direction and requirements](docs/16-project-direction.md)
- [Source register and verification limits](docs/17-source-register.md)
- [Delivery backlog and release gates](docs/18-delivery-backlog.md)

An Apertus 1.5 project for the **Hack Apertus online hackathon**, ending
16 October 2026 at 12:00 CEST / 15:00 Pakistan time.

- [Earlier project idea and phased build plan](PROJECT_IDEA.md)
- [Website review and corrected requirements](docs/11-online-research.md)
- [Current implementation status](track_2a/docs/BUILD_STATUS.md)
- [First live CSCS pilot](docs/12-cscs-pilot.md)
- [Run extraction and the review workbench](track_2a/docs/DEVELOPMENT.md)
- [Run and update the Docker/replay version](track_2a/docs/RUNNING.md)
- [Batch extraction, replay and review import](track_2a/docs/BATCH_EVALUATION.md)
- [Verified pipeline results and remaining limits](track_2a/docs/PIPELINE_VERIFICATION.md)
- [A1–A7 contracts, scoped review and verification](track_2a/docs/AUDIT_IMPLEMENTATION.md)
- [Active technical report draft](track_2a/technical_report.md)

The active challenge directory is `track_2a/`. Earlier files about Liebefeld are
historical planning material. Their broad feature lists and illustrative targets
are not implemented capabilities or measured results.

This project is still in development. CSCS access and an initial real-document
pilot work. The review workbench supports original pages, source checks, persistent
corrections, audit history and reviewed-only exports. Docker/Compose/Makefile
packaging and a public synthetic practice demo are now implemented. Clean-source
startup, PDF preview and review persistence passed; the container image itself
still needs a Docker-enabled build/run check. Reviewed-corpus evaluation is pending.

## Docker requirements

- Docker Engine or Docker Desktop configured for Linux containers, plus Docker
  Compose v2 with `up --wait`; GNU Make is needed only for the `make run` shortcut.
- Internet access for the first image build. The replay demo needs no local Python
  install, API key, model weights or GPU; Poppler is included in the image.
- Port `8765` available on the host by default. Set `SKONY_PORT` to use another
  host port.
- Compose keeps uploaded PDFs, reviews and audit history in the named
  `review-state` volume. Standard rebuilds and `make down` preserve it. Live model
  extraction is optional and needs endpoint settings and an API key in `track_2a/.env`.

Start from the repository root with `make run`, or follow the [Docker running
guide](track_2a/docs/RUNNING.md) for the direct Compose command and verification
status.

Batch extraction now checkpoints every source row, preserves failures, and
caches exact model requests. A real DE/FR pair replayed with two cache hits and
zero model calls. Both saved results are available in the existing workbench;
its 12 existing field decisions were preserved.

The current **245 Python engineering tests and 16 interface-controller tests passed on 16 October 2026**. The v0.2
contracts add dependency-aware scoped review, immutable offline comparison,
legacy migration, explicit gold eligibility/scoring and capability-based citations
at `/scoped`. The main extraction screen still uses v0.1. New checks are synthetic;
corpus-level model accuracy and human gold evaluation remain unmeasured.
Documentation describing broader features is
labelled historical or target design; it does not establish implementation.
