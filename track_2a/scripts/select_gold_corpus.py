"""Select a stratified gold-set corpus from the live OpenParlData API.

Groups each target body's documents by affair, prefers affairs that contain
both a request document and a government-response document, and emits a
stratified candidate manifest for human annotation.

This script reads public metadata only. It downloads no PDFs and makes no
model calls. Output is a selection manifest the fetcher consumes.

Usage:
    python scripts/select_gold_corpus.py [--out data/private/gold_candidates.json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.openparldata.ch/v1"

# Target bodies chosen for language and government-level diversity, per the
# sprint plan (docs/13). body_key is the stable public key used by the files server.
TARGET_BODIES = [
    # German, municipal
    {"body_key": "743", "label": "Nidau", "level": "municipal", "language": "de"},
    {"body_key": "351", "label": "Bern (city)", "level": "municipal", "language": "de"},
    # German, cantonal
    {"body_key": "BE", "label": "Bern (canton)", "level": "cantonal", "language": "de"},
    {"body_key": "ZH", "label": "Zurich (canton)", "level": "cantonal", "language": "de"},
    # French, cantonal
    {"body_key": "VD", "label": "Vaud (canton)", "level": "cantonal", "language": "fr"},
    # French, municipal
    {"body_key": "2196", "label": "Fribourg (city)", "level": "municipal", "language": "fr"},
    {"body_key": "6621", "label": "Geneve (city)", "level": "municipal", "language": "fr"},
]

# Categories that mark an original member request (submission) document.
REQUEST_CATEGORY_HINTS = ("vorstoss", "original", "interpellation", "postulat",
                          "motion", "anfrage", "initiative")
# Categories that mark an executive answer / decision document.
RESPONSE_CATEGORY_HINTS = ("antwort", "beantwortung", "bericht", "decision",
                           "beschluss", "réponse", "répond", "entscheid",
                           "protokoll", "response", "reply")


def get(client: httpx.Client, url: str, **params) -> dict:
    for attempt in range(3):
        try:
            resp = client.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError:
            time.sleep(1 + attempt)
    return {}


def list_all_docs(client: httpx.Client, body_id: int, cap: int = 150) -> list[dict]:
    """Page through a body's docs, newest first, up to cap entries.

    Newest-first ordering matters: recent affairs are most likely to carry the
    request/response pairing metadata we stratify on, and keeps the per-body
    page count small enough to finish within the deadline window.
    """
    docs = []
    offset, limit = 0, 100
    while len(docs) < cap:
        payload = get(client, f"{API}/bodies/{body_id}/docs", offset=offset, limit=limit)
        data = payload.get("data") or []
        if not data:
            break
        docs.extend(data)
        meta = payload.get("meta") or {}
        if not meta.get("has_more"):
            break
        offset += limit
    return docs[:cap]


# Known body_id for keys where direct lookup needs the numeric id. Resolved
# once from the live API and pinned here to avoid rescanning 2411 bodies.
KNOWN_BODY_IDS = {
    "743": 2281, "351": 353, "BE": 253, "ZH": 275, "VD": 272,
    "2196": 313, "6621": 422,
}


def resolve_body(client: httpx.Client, body_key: str) -> dict | None:
    # The single-body route returns the object directly (not wrapped in data).
    body_id = KNOWN_BODY_IDS.get(str(body_key))
    candidates = [body_id, body_key] if body_id is not None else [body_key]
    for candidate in candidates:
        if candidate is None:
            continue
        payload = get(client, f"{API}/bodies/{candidate}")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if isinstance(data, dict) and data.get("id"):
            return data
    return None


def text_len(doc: dict) -> int:
    return len(doc.get("text") or "")


def classify(doc: dict) -> str:
    """Return 'request', 'response', or 'other' from category metadata."""
    cat = doc.get("category") or {}
    names = " ".join(str(v) for v in cat.values() if v).lower()
    harm = str(doc.get("category_harmonized") or "").lower()
    blob = f"{names} {harm} {str(doc.get('name') or '').lower()}"
    is_request = any(h in blob for h in REQUEST_CATEGORY_HINTS)
    is_response = any(h in blob for h in RESPONSE_CATEGORY_HINTS)
    if is_request and not is_response:
        return "request"
    if is_response:
        return "response"
    if is_request:
        return "request"
    return "other"


def is_scanned(doc: dict) -> bool:
    """Heuristic: a PDF with essentially no extracted text is likely scanned."""
    if (doc.get("format") or "").lower() != "application/pdf":
        return False
    return text_len(doc) < 40


def select_for_body(client: httpx.Client, body: dict, want: int) -> list[dict]:
    body_id = body["id"]
    docs = list_all_docs(client, body_id)
    # Keep only affair-linked PDFs with usable metadata.
    affair_docs = [d for d in docs if d.get("affair_id") and
                   (d.get("format") or "").lower() == "application/pdf"]
    by_affair: dict[int, list[dict]] = defaultdict(list)
    for d in affair_docs:
        by_affair[d["affair_id"]].append(d)

    selected = []
    # Pass 1: affairs with both a request and a response document.
    for affair_id, group in sorted(by_affair.items(), key=lambda kv: -len(kv[1])):
        kinds = {classify(d) for d in group}
        if "request" in kinds and "response" in kinds:
            req = next(d for d in group if classify(d) == "request")
            resp = next(d for d in group if classify(d) == "response")
            selected.append(_entry(body, affair_id, req, "request"))
            selected.append(_entry(body, affair_id, resp, "response"))
            if len(selected) >= want * 2:
                break
    # Pass 2: top up with single-document affairs (still useful for the schema
    # feasibility finding, clearly labelled as unpaired).
    if len(selected) < want * 2:
        seen = {e["openparldata_document_id"] for e in selected}
        for affair_id, group in sorted(by_affair.items(), key=lambda kv: -len(kv[1])):
            d = group[0]
            if d["id"] in seen:
                continue
            selected.append(_entry(body, affair_id, d, classify(d) if classify(d) != "other" else "unpaired"))
            if len(selected) >= want * 2:
                break
    return selected


def _entry(body: dict, affair_id: int, doc: dict, role: str) -> dict:
    return {
        "body_key": body["body_key"],
        "body_id": body["id"],
        "body_label": body.get("name", {}).get("de") or body.get("name", {}).get("en"),
        "openparldata_document_id": doc["id"],
        "affair_id": affair_id,
        "role": role,
        "role_origin": "category_and_filename_heuristic_v0.1",
        "role_review_required": True,
        "level": body.get("selection_level", "unknown"),
        "category": (doc.get("category") or {}).get("de") or (doc.get("category") or {}).get("fr"),
        "language": doc.get("language"),
        "date": doc.get("date"),
        "name": doc.get("name"),
        "source_url": doc.get("url"),
        "retrieved_url": doc.get("url_oparl"),
        "size": doc.get("size"),
        "text_chars": text_len(doc),
        "likely_scanned": is_scanned(doc),
        "format": doc.get("format"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "data" / "private" / "gold_candidates.json"))
    parser.add_argument("--per-body", type=int, default=8, help="target docs per body")
    parser.add_argument("--body-key", action="append", dest="extra_keys", default=[],
                        help="additional body_key to include")
    args = parser.parse_args()

    targets = list(TARGET_BODIES)
    for key in args.extra_keys:
        targets.append({"body_key": key, "label": key, "level": "unknown", "language": "unknown"})

    out = {"selected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "source": f"{API}", "note": "Candidate selection only; PDFs not yet fetched",
           "bodies": [], "documents": []}

    with httpx.Client(follow_redirects=True, headers={"User-Agent": "skony-gold-selector/0.1"}) as client:
        for target in targets:
            started = time.monotonic()
            body = resolve_body(client, target["body_key"])
            if not body:
                print(f"!! could not resolve body_key {target['body_key']}", file=sys.stderr)
                continue
            body["selection_level"] = target["level"]
            entries = select_for_body(client, body, args.per_body)
            print(f"   ({time.monotonic() - started:.1f}s)", flush=True)
            out["bodies"].append({
                "body_key": body["body_key"], "body_id": body["id"],
                "label": body.get("name", {}).get("de") or body.get("name", {}).get("en"),
                "type": body.get("type"), "lang": body.get("lang"),
                "canton": body.get("canton_key"), "selected": len(entries)})
            out["documents"].extend(entries)
            print(f"body {body.get('name', {}).get('de')} ({body['body_key']}): {len(entries)} docs")

    # Stratification summary for the report.
    langs = defaultdict(int)
    levels = defaultdict(int)
    scanned = sum(1 for d in out["documents"] if d["likely_scanned"])
    roles = defaultdict(int)
    for d in out["documents"]:
        langs[d["language"] or "?"] += 1
        roles[d["role"]] += 1
    out["summary"] = {"total_documents": len(out["documents"]),
                      "by_language": dict(langs), "by_role": dict(roles),
                      "likely_scanned": scanned}
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2, ensure_ascii=False))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
