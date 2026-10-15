"""Export human-reviewed gold annotations from a review store.

Walks a workbench review store, keeps only documents whose eight extraction
fields all carry an explicit human decision (confirm / correct / missing),
and writes one gold JSON per document plus an annotation README and a manifest.

Entries whose reviewer marks them as automated QA are excluded: engineering
interface checks are not gold labels and must not be scored as such.

This script makes no model calls and modifies no review data.

Usage:
    python scripts/export_gold.py --store output/workbench --out data/gold
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skony.review import FIELD_NAMES, ReviewStore  # noqa: E402
from skony.cache import atomic_json, digest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Reviewer labels that mark automated interface checks, not human gold. Any
# document with such a reviewer on any field is excluded from the gold set.
QA_MARKERS = ("automated ui qa", "automated", "qa bot", "not gold")


def is_qa(review: dict | None) -> bool:
    if not review:
        return False
    reviewer = str(review.get("reviewer", "")).lower()
    return any(marker in reviewer for marker in QA_MARKERS)


def exclusion_reason(item: dict) -> str | None:
    source = item["source"] or {}
    if source.get("synthetic") or source.get("gold_annotation") is False:
        return "excluded_source"
    reviews = [item["fields"][name]["review"] for name in FIELD_NAMES]
    if any(is_qa(review) for review in reviews):
        return "automated_qa"
    if any(review is None for review in reviews):
        return "incomplete"
    return None


def export_document(store: ReviewStore, identifier: str, *, item=None) -> dict | None:
    item = store.get(identifier) if item is None else item
    if exclusion_reason(item):
        return None
    fields = item["fields"]
    decisions = {}
    qa = False
    for name in FIELD_NAMES:
        review = fields[name]["review"]
        if review is None:
            return None  # incomplete: every field needs an explicit decision
        if is_qa(review):
            qa = True
        decisions[name] = review
    if qa:
        return None  # automated QA document, not human gold
    source = item["source"] or {}
    return {
        "gold_schema_version": "skony.gold.v0.1",
        "document_id": item["document"]["document_id"],
        "document_sha256": item["document"]["sha256"],
        "filename": item["filename"],
        "pages": len(item["document"]["pages"]),
        "textless_pages": item["document"].get("textless_pages", []),
        "source": {**source, "language": source.get("language") or source.get("language_label")},
        "suggestion_origin": {"model": item["model"], "prompt_version": item["prompt_version"],
                              "verifier_version": item["verifier_version"]},
        "decisions": decisions,
        "reviewers": sorted({d.get("reviewer") for d in decisions.values() if d.get("reviewer")}),
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def annotation_readme(manifest: dict) -> str:
    by_lang = manifest["summary"]["by_language"]
    by_body = manifest["summary"]["by_body"]
    lines = [
        "# Gold annotation set",
        "",
        f"Exported: {manifest['exported_at']}  ",
        f"Documents: {manifest['summary']['documents']}  ",
        f"Schema: `skony.gold.v0.1`",
        "",
        "Each `*.json` file holds complete human review decisions for one source",
        "document: every one of the eight extraction fields carries an explicit",
        "confirm / correct / absent decision with provenance. Automated interface",
        "QA entries and synthetic practice documents are excluded from gold.",
        "Only files named in manifest.json belong to this export; their checksums are recorded there.",
        "",
        "## Coverage",
        "",
        "By language: " + ", ".join(f"{k}={v}" for k, v in sorted(by_lang.items())),
        "By body: " + ", ".join(f"{k}={v}" for k, v in sorted(by_body.items())),
        "",
        "## Reviewer-competence disclosure",
        "",
        manifest.get("reviewer_note") or (
            "See docs/ANNOTATION_GUIDE.md for the review procedure and field "
            "decision rules."),
        "",
        "## Decision semantics",
        "",
        "- `confirmed`: the located source passage was verified as the correct value.",
        "- `corrected`: the reviewer supplied the value and the supporting passage.",
        "- `absent`: a competent reviewer checked the relevant source scope and found the field absent.",
        "- Unreadable or uncertain fields stay unreviewed and exclude the document from this complete gold set.",
        "",
        "The original PDF remains authoritative; these decisions record what a human",
        "verified against it.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default=str(ROOT / "output" / "workbench"))
    parser.add_argument("--out", default=str(ROOT / "data" / "gold"))
    parser.add_argument("--reviewer-note", default="",
                        help="disclosure line for the annotation README")
    args = parser.parse_args()

    store_dir = Path(args.store)
    if not (store_dir / "review.sqlite3").is_file():
        print(f"No review store at {store_dir}", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()):
        print("Gold output directory is not empty. Choose a new directory so stale labels cannot enter this export.", file=sys.stderr)
        return 2
    store = ReviewStore(store_dir, read_only=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    exported, files = [], []
    skipped = {"incomplete": 0, "automated_qa": 0, "excluded_source": 0}
    for summary in store.list():
        identifier = summary["id"]
        item = store.get(identifier)
        reason = exclusion_reason(item)
        if reason:
            skipped[reason] += 1
            continue
        record = export_document(store, identifier, item=item)
        if record is None:
            skipped["incomplete"] += 1
            continue
        # Filenames never incorporate uncontrolled source labels or paths.
        sha = record["document_sha256"]
        safe_sha = sha if re.fullmatch(r"[0-9a-f]{64}", sha) else digest(sha)
        fname = f"document_{safe_sha}.json"
        atomic_json(out_dir / fname, record)
        files.append({"file": fname, "document_sha256": sha, "record_sha256": digest(record)})
        exported.append(record)

    by_lang: dict[str, int] = {}
    by_body: dict[str, int] = {}
    for record in exported:
        lang = record["source"]["language"] or "unknown"
        body = record["source"].get("body_label") or record["source"].get("body_key") or "unknown"
        by_lang[lang] = by_lang.get(lang, 0) + 1
        by_body[body] = by_body.get(body, 0) + 1

    manifest = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "store": str(store_dir),
        "reviewer_note": args.reviewer_note,
        "files": files,
        "summary": {"documents": len(exported),
                    "skipped_incomplete": skipped["incomplete"],
                    "skipped_automated_qa": skipped["automated_qa"],
                    "skipped_excluded_source": skipped["excluded_source"],
                    "by_language": by_lang, "by_body": by_body},
    }
    (out_dir / "README.md").write_text(annotation_readme(manifest), encoding="utf-8")
    # A manifest appears only after every listed record has been written.
    atomic_json(out_dir / "manifest.json", manifest)
    print(json.dumps(manifest["summary"], indent=2, ensure_ascii=False))
    print(f"wrote {len(exported)} gold files to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
