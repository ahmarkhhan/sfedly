"""Prepare a local source-first review desk from frozen real corpus evidence."""
import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skony.contracts import FIELDS, TextSnapshot, identity

# A transparent convenience sample, not a random or representative benchmark.
SELECTED = [0, 6, 12, 16, 24, 25, 32, 33, 36, 37, 38, 43]
TITLES = {
    0: "Perspektiven für KMU und lokale Geschäfte",
    6: "Digitale Souveränität - Handeln bevor es zu spät ist.",
    12: "Dringliche Interfraktionelle Interpellation: «Abriss auf Vorrat» an der Weissensteinstrasse 4/4a – die Stadt Bern und Freiräume, Kultur und nachhaltige Stadtentwicklung",
    16: "Transparente Kosten und Organisation der Plattform ePublikation",
    24: "Anhebung Grenze Hochhaus",
    25: "Planungs- und Baugesetz (PBG)",
    32: "Mise en consultation publique de la révision de la LRou / avant-projet LMob",
    33: "Révision de la loi du 9 mai 1983 sur le contrôle des habitants",
    36: "Vergerette annuelle",
}
ROLES = {0: "submission", 6: "submission", 12: "decision_record", 16: "submission",
         24: "submission", 25: "unknown", 32: "unknown", 33: "unknown", 36: "annex",
         37: "submission", 38: "submission", 43: "submission"}


def anchor(text, needle):
    pattern = r"\s+".join(re.escape(part) for part in needle.split())
    for page in text.pages:
        match = re.search(pattern, page.text, re.IGNORECASE)
        if match:
            return {"value": match.group(), "evidence": {
                "artifact_id": text.artifact_id, "text_snapshot_id": text.id,
                "page": page.page, "layer_id": page.layer_id, "start": match.start(),
                "end": match.end(), "quote": match.group()}}
    return None


def freeze_pilot_predictions(pack, out, results_dir=None):
    """Freeze existing production results separately; never reveal them in the desk."""
    results_dir = results_dir or ROOT / "output/pipeline-proof-20261016-012105-2ff326/first/results"
    target = out / "locked-predictions.json"
    if target.exists():
        raise ValueError("Locked pilot predictions already exist; do not replace them")
    docs = {d["id"]: d for d in pack["documents"]}
    predictions = []
    result_dir = out / "model-results"
    result_dir.mkdir(exist_ok=False)
    for path in sorted(results_dir.rglob("*.json")):
        raw = path.read_bytes()
        result = json.loads(raw)
        doc_id = result.get("document", {}).get("sha256")
        if doc_id not in docs:
            continue
        expected = {p["page"]: p["text"] for p in docs[doc_id]["text"]["pages"]}
        actual = {p["number"]: p["text"] for p in result["document"]["pages"]}
        if actual != expected:
            raise ValueError("Saved pilot result uses a different source-text projection")
        file_digest = hashlib.sha256(raw).hexdigest()
        relative = "model-results/" + file_digest + ".json"
        (out / relative).write_bytes(raw)
        predictions.append({"document_id": doc_id, "result_file": relative, "file_sha256": file_digest,
            "model": result["model_name"], "prompt_version": result["prompt_version"],
            "verifier_version": result["verifier_version"]})
    lock = {"schema_version": "skony.fast-review-predictions.v1", "pack_digest": pack["digest"],
        "locked_at": datetime.now(timezone.utc).isoformat(), "predictions": predictions,
        "purpose": "Previously recorded production outputs, hidden from the review UI. Only subsequent source-only annotations can enter the single-reviewer pilot comparison."}
    lock["digest"] = identity(lock)
    target.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    return lock


def build(out, source_dir=None, preflight=None):
    source_dir = source_dir or ROOT / "data/private/gold"
    preflight = preflight or ROOT / "output/evaluation-audit-20261016/coverage-preflight-with-structure"
    manifest = json.loads((source_dir / "fetch_manifest.json").read_text(encoding="utf-8"))
    intake = json.loads((preflight / "intake-review-packet.json").read_text(encoding="utf-8"))
    texts = {t["artifact_id"]: TextSnapshot.model_validate(t) for t in intake["texts"]}
    units = {u["artifact_id"]: u for u in intake["units"] if u["artifact_id"]}
    documents = []
    for index in SELECTED:
        row = manifest["documents"][index]
        digest = row["sha256"]
        pdf = source_dir / row["document_file"]
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != digest:
            raise ValueError("Pinned PDF digest differs: " + str(pdf))
        text = texts[digest]
        language = "fr" if row["body_key"] in {"VD", "6621"} else "de"
        level = "cantonal" if row["body_key"] in {"BE", "ZH", "VD"} else "municipal"
        suggestions = {}
        title = TITLES.get(index)
        if title:
            suggestion = anchor(text, title)
            if suggestion:
                suggestions["title"] = suggestion
        elif index in {37, 38, 43}:
            match = re.search(r"«(.*?)»", text.pages[0].text, re.S)
            if match:
                suggestions["title"] = anchor(text, match.group(1))
        raw = "Interpellation" if index in {0, 16} else "Postulat" if index == 6 else "Motion" if index in {37, 43} else "Question écrite" if index == 38 else None
        if raw:
            suggestions["affair_type_raw"] = anchor(text, raw)
        if index == 24:
            suggestions["affair_type_raw"] = anchor(text, "P A R L A M E N T A R I S C H E I N I T I A T I V E")
        dates = {16: "05.10.2026", 24: "4. September 2023", 37: "23 juin 2026", 38: "28 septembre 2026", 43: "28 septembre 2026"}
        if index in dates:
            suggestions["submitted_date_raw"] = anchor(text, dates[index])
        if index == 16:
            suggestions["submitter_raw"] = anchor(text, "Zulliger (Gerzensee, SVP) (Sprecher/in)")
        if index == 12:
            suggestions["decision_raw"] = anchor(text, "Die Einreichenden sind mit der Antwort nicht zufrieden.")
            suggestions["decision_date_raw"] = anchor(text, "20. August 2026")
        suggestions = {k: v for k, v in suggestions.items() if v is not None}
        notes = {
            12: "The manifest calls this a response, but the source heading says Stadtratsbeschluss. Check role and distinguish a recorded reaction from the executive answer itself.",
            25: "Commission legislative draft/report: do not infer that 'beschliesst' is a final adopted decision or that this is an executive answer. Committee-report role is missing from the current closed role list.",
            32: "Public consultation letter. A letter date is not automatically a parliamentary submission date. Verify affair membership separately.",
            33: "Public consultation letter with extraction noise. Verify the PDF and affair membership; preserve unavailable parliamentary fields.",
            36: "Technical invasive-species attachment. Check diagrams/tables in the PDF: the eight parliamentary fields do not describe all technical content. Attachment membership is only a metadata hint.",
            24: "Spaced lettering and line-break hyphenation occur in the extracted text. Preserve source quotations rather than inventing cleaner offsets.",
        }.get(index, "Review the original PDF. A source-only record cannot establish whether an answer exists elsewhere in the affair.")
        documents.append({"id": digest, "manifest_index": index, "filename": row["document_file"],
            "pdf": "pdfs/" + digest + ".pdf", "source_url": row["source_url"],
            "display_name": row.get("name", row["document_file"]), "body_label": row["body_label"],
            "unit": units[digest], "text": text.model_dump(), "text_snapshot_id": text.id,
            "hints": {"language": language, "level": level, "role": ROLES[index]},
            "suggestions": suggestions, "review_note": notes})
    body = {"schema_version": "skony.fast-review-pack.v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_cohort_digest": intake["candidate_cohort_digest"], "fields": list(FIELDS),
        "design": "Purposive 12-document convenience sample: 3 per hinted language/level cell. Not a representative accuracy benchmark. Source-first annotations and suggestion-exposed annotations are kept distinct.",
        "documents": documents,
        "question": "Which printed parliamentary instruments occur in the selected Nidau and Geneva submissions?",
        "schema_tasks": [
            {"id": "raw-type", "statement": "The raw-type string can retain German and French instrument names, but translation alone does not prove legal equivalence.", "document_indices": [0, 6, 37, 38]},
            {"id": "role-boundary", "statement": "A commission legislative draft needs distinct role semantics; labeling it an executive response or a final adopted decision would lose meaning.", "document_indices": [25]},
            {"id": "decision-answer", "statement": "A city record of dissatisfaction with an answer is distinct from the executive answer text itself.", "document_indices": [12]},
            {"id": "annex-boundary", "statement": "The eight parliamentary fields do not fully represent technical tables, diagrams or intervention guidance in an attached fact sheet; retain the original attachment and scoped provenance.", "document_indices": [36]},
        ]}
    body["digest"] = identity(body)
    out.mkdir(parents=True, exist_ok=False)
    (out / "pdfs").mkdir()
    for doc in documents:
        shutil.copyfile(source_dir / doc["filename"], out / doc["pdf"])
    (out / "review-pack.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "pack.js").write_text("window.REVIEW_PACK = " + json.dumps(body, ensure_ascii=False).replace("</", "<\\/") + ";", encoding="utf-8")
    shutil.copyfile(ROOT / "src/skony/static/fast_review.html", out / "index.html")
    freeze_pilot_predictions(body, out)
    (out / "README.md").write_text("# Review now\n\nOpen index.html in a browser, or serve this folder locally. Start with source-only review; reveal suggestions only if assistance is needed. Enter your name and actual language competence. Confirm intake after opening the PDF and checking body/affair identity. Review at least title and raw instrument type on the submission documents. Unknowns stay unknown. All eight fields and all PDF pages are available.\n\nExport review.json, then run:\n\n    python scripts/finalize_fast_review.py --pack PATH/review-pack.json --review PATH/review.json --out output/review-results-new\n\nThis creates a checked review summary, a new cohort containing only actual confirmed intake, and a cross-body answer only where reviewed records support it. Suggestions shown before field review make that field assisted; these records are not independent blind gold. This local pack contains source PDFs; review redistribution rights before publishing.\n", encoding="utf-8")
    return body


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = build(args.out)
    print(json.dumps({"documents": len(result["documents"]), "pack_digest": result["digest"], "review_page": str(args.out / "index.html")}))
