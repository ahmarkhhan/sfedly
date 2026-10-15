"""Retrieve the selected public Nidau postulate, without inference credentials."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "data" / "private"
    rows = [json.loads(line) for line in (directory / "nidau_metadata_sample.ndjson").read_text(encoding="utf-8").splitlines()]
    row = next(row for row in rows if row["id"] == 883029)
    url = row["url_oparl"]
    contents = bytearray()
    try:
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            for _ in range(4):
                parsed = urlsplit(url)
                if parsed.scheme != "https" or parsed.hostname not in {"www.nidau.ch", "nidau.ch", "files.openparldata.ch"}:
                    print("Pilot source redirect left the selected public source websites")
                    return 2
                with client.stream("GET", url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    if response.status_code != 200:
                        print("Municipal PDF HTTP", response.status_code)
                        return 3
                    content_type = response.headers.get("content-type", "")
                    for chunk in response.iter_bytes():
                        contents.extend(chunk)
                        if len(contents) > 2 * 1024 * 1024:
                            print("Pilot PDF exceeds the 2 MB sample limit")
                            return 2
                    break
            else:
                print("Too many source redirects")
                return 2
        if not contents.startswith(b"%PDF-"):
            print("Selected municipal source did not return a PDF")
            return 2
        path = directory / "nidau-postulate-2013.pdf"
        path.write_bytes(contents)
        digest = hashlib.sha256(contents).hexdigest()
        manifest = {
            "document_file": path.name, "source_url": row["url"], "retrieved_url": url,
            "metadata_source": "https://files.openparldata.ch/exports/docs/docs_743.ndjson.gz",
            "openparldata_document_id": row["id"], "body_id": row["body_id"], "body_key": row["body_key"],
            "metadata_name": row["name"], "metadata_language": row["language"],
            "metadata_parent_type": row["parent_type"], "metadata_affair_id": row["affair_id"],
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "sha256": digest,
            "metadata_hash": row["hash"], "metadata_hash_matches": digest == row["hash"],
            "content_type": content_type, "bytes": len(contents),
            "licence_status": "not yet verified for redistribution; local engineering pilot",
        }
        (directory / "pilot_source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"file": path.name, "bytes": len(contents), "metadata_hash_matches": digest == row["hash"]}))
        return 0
    except httpx.HTTPError as error:
        print("Public PDF connection failed:", type(error).__name__)
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
