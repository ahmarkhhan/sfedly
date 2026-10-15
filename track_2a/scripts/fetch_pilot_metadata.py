"""Download one small public OpenParlData export for local pilot selection."""

import gzip
import json
from io import BytesIO
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
URL = "https://files.openparldata.ch/exports/docs/docs_743.ndjson.gz"


def main():
    try:
        content = bytearray()
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            with client.stream("GET", URL) as response:
                if response.status_code != 200:
                    print("Public metadata endpoint HTTP", response.status_code)
                    return 3
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 12 * 1024 * 1024:
                        print("Metadata exceeds the pilot download limit")
                        return 2
        rows = []
        used = 0
        with gzip.GzipFile(fileobj=BytesIO(content)) as source:
            while len(rows) < 200:
                line = source.readline(1024 * 1024)
                used += len(line)
                if not line or used > 10 * 1024 * 1024:
                    break
                if not line.endswith(b"\n"):
                    print("Record exceeds bounded pilot reader limit")
                    return 2
                rows.append(json.loads(line))
        directory = ROOT / "data" / "private"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "nidau_metadata_sample.ndjson").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
        print("Pilot metadata records:", len(rows))
        for row in rows[:3]:
            print(json.dumps({"keys": sorted(row), "sample": {k: v for k, v in row.items()
                              if k in {"id", "body_id", "url", "file_url", "download_url", "source_url", "filename", "title"}}}, ensure_ascii=True))
        return 0
    except httpx.HTTPError as error:
        print("Public metadata connection failed:", type(error).__name__)
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
