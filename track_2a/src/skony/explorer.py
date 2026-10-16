"""Read-only research over local PDFs, with conservative document-level evidence.

This projection does not create scoped approvals, gold labels or inferred Q/A
links. Metadata dossiers are explicitly unverified source associations.
"""

import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from urllib.parse import urlencode, urlsplit

from .review import FIELD_NAMES, ReviewError, timestamp

SCHEMA = "skony.research-brief.v1"
# Discovery hints only; raw affair semantics and controlled vocabularies stay separate.
TOPICS = {
    "transport": ("Transport", "verkehr bahn bus mobilit velo cycl radweg tram transport trasport traffic"),
    "housing": ("Housing", "wohn miet logement loyer habitat alloggi abitaz housing rent"),
    "climate": ("Climate & energy", "klima energie energ environment umwelt climat environnement ambiente"),
    "finance": ("Public finance", "budget finanz steuer depense impots fiscal finanz spesa"),
    "education": ("Education", "schule schul bildung ecole enseign formation scuola istruz education"),
    "health": ("Health", "gesund spital sante hopital sanita ospedal health hospital"),
    "digital": ("Digital services", "digital numerique informatique informatic daten data"),
}


def folded(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold())
                   if not unicodedata.combining(c))


def words(text):
    return re.findall(r"\w+", folded(text), flags=re.UNICODE)


def safe_url(value):
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme in {"https", "http"} and parts.hostname and not parts.username and not parts.password:
            return value
    except ValueError:
        pass
    return None


def iso_date(value):
    """Sort only unambiguous numeric dates; retain original wording in every event."""
    if not value:
        return None
    match = re.fullmatch(r"\s*(\d{4})-(\d{2})-(\d{2})\s*", value)
    if match:
        parts = list(map(int, match.groups()))
    else:
        match = re.fullmatch(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s*", value)
        if not match:
            return None
        day, month, year = map(int, match.groups())
        parts = [year, month, day]
    try:
        return date(*parts).isoformat()
    except ValueError:
        return None


class Explorer:
    def __init__(self, store):
        self.store = store

    def _documents(self, reviewed_only):
        # One SQLite read snapshot prevents a brief mixing fields from two revisions.
        with self.store.db() as db:
            db.execute("BEGIN")
            rows = list(db.execute("SELECT id,filename,document_json,source_json,result_json,revision FROM documents ORDER BY id"))
            reviews = {(r["document_id"], r["field"]): json.loads(r["review_json"]) for r in
                       db.execute("SELECT document_id,field,review_json FROM reviews")}
        output = []
        for row in rows:
            document, source = json.loads(row["document_json"]), json.loads(row["source_json"])
            result = json.loads(row["result_json"]) if row["result_json"] else None
            fields = {}
            for name in FIELD_NAMES:
                review = reviews.get((row["id"], name))
                proposal = result["fields"].get(name) if result else None
                effective = review if review is not None else (proposal if not reviewed_only else None)
                value = effective.get("value") if effective else None
                provenance = effective.get("provenance") if effective else None
                # No provenance, no research assertion. A reviewer absence is kept explicitly.
                if value is not None and provenance is None:
                    value = None
                fields[name] = {"value": value,
                    "status": ("document_reviewed" if review is not None else
                               "source_located_unreviewed" if value is not None else
                               "withheld_unreviewed" if reviewed_only and proposal and proposal.get("value") is not None else "not_located"),
                    "review_decision": review.get("decision") if review else None,
                    "reviewer": review.get("reviewer") if review else None,
                    "citation": ({**provenance, "document_id": row["id"],
                        "pdf_url": f'/api/documents/{row["id"]}/pdf#page={provenance["page"]}',
                        "review_url": "/?" + urlencode({"document": row["id"], "field": name,
                                                       "page": provenance["page"]})} if provenance and value is not None else None)}
            language = source.get("language") or source.get("metadata_language") or source.get("language_label") or "unknown"
            language = {"german": "de", "french": "fr", "italian": "it", "english": "en"}.get(str(language).casefold(), str(language).casefold())
            body_id = source.get("body_id")
            body_value = body_id if body_id is not None else source.get("body_key")
            body_key = ("id:" if body_id is not None else "key:") + str(body_value) if body_value is not None else "unknown"
            affair_id = source.get("affair_id")
            if affair_id is None:
                affair_id = source.get("metadata_affair_id")
            provider = source.get("provider_namespace") or ("openparldata" if source.get("openparldata_document_id") is not None else "unknown")
            synthetic = bool(source.get("synthetic"))
            # Incomplete identity never merges two documents or two parliaments.
            complete_identity = affair_id not in (None, "") and body_value not in (None, "") and provider != "unknown"
            group = ([synthetic, provider, body_key, str(affair_id)]
                     if complete_identity else ["document", row["id"]])
            output.append({"id": row["id"], "filename": row["filename"], "revision": row["revision"],
                "sha256": document["sha256"], "fields": fields, "pages": document["pages"],
                "textless_pages": document.get("textless_pages", []), "model": result.get("model_name") if result else None,
                "body": source.get("body_label") or body_key, "body_key": body_key,
                "body_source_key": str(source.get("body_key") or body_value or "unknown"), "language": language,
                "level": source.get("level") or "unknown", "synthetic": synthetic,
                "affair_id": affair_id, "provider": provider,
                "source_url": safe_url(source.get("source_url")), "role_hint": source.get("role"),
                "rights_status": source.get("licence_status") or source.get("licence") or "unknown",
                "association_status": "unverified_source_metadata" if complete_identity else "single_document",
                "group_id": hashlib.sha256(json.dumps(group, ensure_ascii=False).encode()).hexdigest()})
        return output

    def _dossiers(self, reviewed_only=False):
        groups = {}
        documents = self._documents(reviewed_only)
        body_labels = {}
        for doc in documents:
            key = doc["body_key"]
            if key not in body_labels or len(doc["body"]) < len(body_labels[key]):
                body_labels[key] = doc["body"]
        for doc in documents:
            label = body_labels[doc["body_key"]]
            doc["body"] = (label + " · " + doc["body_source_key"] if
                           sum(v == label for v in body_labels.values()) > 1 else label)
            groups.setdefault(doc["group_id"], []).append(doc)
        dossiers = []
        for identifier, documents in groups.items():
            first = documents[0]
            title_fields = [d["fields"]["title"] for d in documents if d["fields"]["title"]["value"]]
            title_fields.sort(key=lambda f: f["status"] != "document_reviewed")
            text = "\n".join(p["text"] for d in documents for p in d["pages"])
            source_words = set(words(text))
            topics = [key for key, (_, stems) in TOPICS.items()
                      if any(any(w.startswith(stem) for w in source_words) for stem in stems.split())]
            fields = [f for d in documents for f in d["fields"].values()]
            dossiers.append({"id": identifier, "title": title_fields[0]["value"] if title_fields else first["filename"],
                "body": first["body"], "body_key": first["body_key"], "languages": sorted({d["language"] for d in documents}),
                "levels": sorted({d["level"] for d in documents}), "synthetic": first["synthetic"],
                "affair_id": first["affair_id"], "provider": first["provider"],
                "association_status": first["association_status"],
                "topics": topics, "document_count": len(documents), "documents": documents,
                "page_count": sum(len(d["pages"]) for d in documents),
                "textless_page_count": sum(len(d["textless_pages"]) for d in documents),
                "reviewed_fields": sum(f["status"] == "document_reviewed" for f in fields),
                "located_fields": sum(f["value"] is not None for f in fields),
                "has_request": any(d["fields"]["question_text"]["value"] for d in documents),
                "has_answer": any(d["fields"]["answer_text"]["value"] for d in documents),
                "has_decision": any(d["fields"]["decision_raw"]["value"] for d in documents),
                "_search": folded(text + "\n" + "\n".join(
                    [d["filename"] + " " + d["body"] + " " + str(d["affair_id"] or "") + " " +
                     " ".join(f["value"] or "" for f in d["fields"].values()) for d in documents]))})
        return sorted(dossiers, key=lambda d: (folded(d["body"]), folded(d["title"]), d["id"]))

    @staticmethod
    def filters(params):
        allowed = {"q", "body", "language", "topic", "evidence", "sources", "reviewed_only", "offset", "limit", "format"}
        if set(params) - allowed:
            raise ReviewError("Unknown explorer filter")
        result = {k: params.get(k, "") for k in ("q", "body", "language", "topic", "evidence")}
        result["q"] = result["q"].strip()
        if len(result["q"]) > 250:
            raise ReviewError("Search is limited to 250 characters")
        result["sources"] = params.get("sources", "all")
        if result["sources"] not in {"all", "real", "practice"} or result["topic"] not in {"", *TOPICS}:
            raise ReviewError("Unknown source or topic filter")
        if result["evidence"] not in {"", "request", "answer", "decision", "no_answer", "needs_extraction"}:
            raise ReviewError("Unknown evidence filter")
        if params.get("reviewed_only", "false") not in {"true", "false"}:
            raise ReviewError("Choose true or false for reviewed fields")
        result["reviewed_only"] = params.get("reviewed_only") == "true"
        return result

    def select(self, params):
        filters = self.filters(params)
        all_dossiers = self._dossiers(filters["reviewed_only"])
        terms = words(filters["q"])
        selected = []
        for dossier in all_dossiers:
            if filters["sources"] == "real" and dossier["synthetic"] or filters["sources"] == "practice" and not dossier["synthetic"]:
                continue
            if filters["body"] and dossier["body_key"] != filters["body"]:
                continue
            if filters["language"] and filters["language"] not in dossier["languages"]:
                continue
            if filters["topic"] and filters["topic"] not in dossier["topics"]:
                continue
            if not all(term in dossier["_search"] for term in terms):
                continue
            evidence = filters["evidence"]
            if evidence in {"request", "answer", "decision"} and not dossier["has_" + evidence]:
                continue
            if evidence == "no_answer" and dossier["has_answer"]:
                continue
            if evidence == "needs_extraction" and any(d["model"] for d in dossier["documents"]):
                continue
            selected.append(dossier)
        return filters, all_dossiers, selected

    @staticmethod
    def snippet(dossier, query):
        terms = words(query)
        best, best_score = None, -1
        for doc in dossier["documents"]:
            for page in doc["pages"]:
                tokens = list(re.finditer(r"\w+", page["text"]))
                hits = [m for m in tokens if any(term in folded(m.group()) for term in terms)]
                score = len({term for term in terms if term in folded(page["text"])})
                if page["text"].strip() and score > best_score:
                    center = hits[0].start() if hits else 0
                    start, end = max(0, center - 100), min(len(page["text"]), center + 260)
                    best = {"document_id": doc["id"], "page": page["number"], "start": start, "end": end,
                            "quote": page["text"][start:end], "basis": "source_text_search",
                            "pdf_url": f'/api/documents/{doc["id"]}/pdf#page={page["number"]}'}
                    best_score = score
        return best

    @staticmethod
    def summary(dossier):
        return {k: v for k, v in dossier.items() if k not in {"documents", "_search"}}

    @staticmethod
    def insights(selected):
        return {"dossiers": len(selected), "documents": sum(d["document_count"] for d in selected),
                "bodies": len({d["body_key"] for d in selected if d["body_key"] != "unknown"}),
                "with_request_text": sum(bool(d["has_request"]) for d in selected),
                "with_answer_text": sum(bool(d["has_answer"]) for d in selected),
                "with_decision_text": sum(bool(d["has_decision"]) for d in selected),
                "practice_dossiers": sum(d["synthetic"] for d in selected),
                "pages_needing_ocr": sum(d["textless_page_count"] for d in selected),
                "by_body": [dict(body=k[1], body_key=k[0], dossiers=v) for k, v in
                            sorted(Counter((d["body_key"], d["body"]) for d in selected).items())]}

    def search(self, params):
        filters, all_dossiers, selected = self.select(params)
        try:
            offset, limit = int(params.get("offset", "0")), int(params.get("limit", "30"))
        except ValueError:
            raise ReviewError("Invalid search pagination") from None
        if offset < 0 or not 1 <= limit <= 100:
            raise ReviewError("Search limit must be 1–100 and offset nonnegative")
        return {"schema_version": "skony.explorer.v1", "filters": filters, "total": len(selected),
            "offset": offset, "limit": limit, "insights": self.insights(selected),
            "facets": {"bodies": [dict(key=k, label=v) for k, v in sorted({(d["body_key"], d["body"]) for d in all_dossiers})],
                       "languages": sorted({v for d in all_dossiers for v in d["languages"]}),
                       "topics": [dict(key=k, label=v[0]) for k, v in TOPICS.items()]},
            "results": [{**self.summary(d), "snippet": self.snippet(d, filters["q"])} for d in selected[offset:offset + limit]],
            "scope_note": "Local imported PDFs only. Counts describe located text, not official procedural status. Topic tags are keyword hints. Metadata links are unverified."}

    def detail(self, identifier, *, reviewed_only=False):
        dossier = next((d for d in self._dossiers(reviewed_only) if d["id"] == identifier), None)
        if dossier is None:
            raise ReviewError("Dossier not found", 404)
        timeline, actors = [], []
        for doc in dossier["documents"]:
            fields = doc["fields"]
            for kind, predicate, date_field in [("Request / question", "question_text", "submitted_date_raw"),
                                               ("Government answer", "answer_text", None),
                                               ("Decision", "decision_raw", "decision_date_raw")]:
                content = fields[predicate]
                dated = fields[date_field] if date_field else None
                if not content["value"] and not (dated and dated["value"]):
                    continue
                raw_date = dated["value"] if dated else None
                timeline.append({"kind": kind, "document_id": doc["id"], "field": predicate,
                    "date_raw": raw_date, "date_iso": iso_date(raw_date),
                    "date_evidence": dated, "content": content})
            actor = fields["submitter_raw"]
            if actor["value"]:
                actors.append({"role": "Submitter / signatory block", "document_id": doc["id"], **actor})
        timeline.sort(key=lambda e: (e["date_iso"] is None, e["date_iso"] or "", e["document_id"], e["kind"]))
        return {**self.summary(dossier), "schema_version": "skony.dossier.v1", "documents": dossier["documents"],
                "timeline": timeline, "actors": actors,
                "note": "Document-level fields. No question/answer pairing or actor identity is inferred. Unsorted date wording remains in the undated section. Scoped approvals are separate."}

    def brief(self, params):
        filters, _, selected = self.select(params)
        return {"schema_version": SCHEMA, "exported_at": timestamp(), "filters": filters,
                "scope": "Local document research; not a scoped reviewed export or gold annotation.",
                "interpretation": "Absence of located text does not establish that the government has not answered or decided. Metadata dossier associations are unverified.",
                "insights": self.insights(selected),
                "dossiers": [{**self.summary(d), "documents": [{k: v for k, v in doc.items() if k != "pages"}
                              for doc in d["documents"]]} for d in selected]}

    @staticmethod
    def csv(brief):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["dossier_id", "body", "affair_id", "synthetic", "document_id", "sha256", "revision",
                         "field", "value", "status", "reviewer", "page", "quote", "pdf_path", "source_url"])
        for dossier in brief["dossiers"]:
            for doc in dossier["documents"]:
                for name, field in doc["fields"].items():
                    citation = field["citation"] or {}
                    cells = [dossier["id"], dossier["body"], dossier["affair_id"], dossier["synthetic"],
                             doc["id"], doc["sha256"], doc["revision"], name, field["value"], field["status"],
                             field["reviewer"], citation.get("page"), citation.get("quote"),
                             citation.get("pdf_url"), doc["source_url"]]
                    # A public-source string must never execute as a spreadsheet formula.
                    writer.writerow([("'" + c if c.lstrip().startswith(("=", "+", "-", "@")) or c.startswith(("\t", "\r", "\n")) else c)
                                     if isinstance(c, str) else c for c in cells])
        return stream.getvalue().encode("utf-8-sig")
