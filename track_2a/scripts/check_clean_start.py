"""Exercise a clean public source copy using the current Python dependencies.

This is not a Docker build check. It does not use or modify the user's workbench.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def running(package: Path, state: Path, log: Path):
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY", "SKONY_MODE", "SKONY_DATA_DIR"}}
    environment["PYTHONPATH"] = str(package / "src")
    environment["PYTHONUNBUFFERED"] = "1"
    # Port zero asks the operating system to choose an unused loopback port.
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-m", "skony", "serve", "--port", "0", "--mode", "replay",
             "--data-dir", str(state)], cwd=package, env=environment, stdout=output, stderr=output,
        )
        try:
            deadline = time.monotonic() + 15
            base = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Clean source application exited before startup")
                text = log.read_text(encoding="utf-8")
                if "http://127.0.0.1:" in text:
                    base = text.split("http://127.0.0.1:", 1)[1].split()[0]
                    break
                time.sleep(0.05)
            if base is None:
                raise RuntimeError("Clean source application did not become ready")
            with httpx.Client(base_url="http://127.0.0.1:" + base, trust_env=False, timeout=40) as client:
                yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def checked(response):
    response.raise_for_status()
    return response


def main():
    parent = ROOT / "tmp"
    parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clean-start-", dir=parent) as temporary:
        directory = Path(temporary)
        package = directory / "package"
        package.mkdir()
        for name in ("src", "web", "data/sample"):
            shutil.copytree(ROOT / name, package / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        assert not (package / ".env").exists()
        assert not (package / "data/private").exists()
        assert not (package / "output").exists()
        state = directory / "persistent-state"
        with running(package, state, directory / "first.log") as client:
            assert checked(client.get("/healthz")).json()["status"] == "ok"
            initial = checked(client.get("/api/state")).json()
            assert initial["mode"] == "replay" and not initial["api_configured"]
            assert len(initial["documents"]) == 1
            identifier = initial["documents"][0]["id"]
            path = f"/api/documents/{identifier}"
            document = checked(client.get(path)).json()
            assert document["extraction_origin"] == "synthetic_fixture"
            assert checked(client.get(path + "/pdf")).content.startswith(b"%PDF-")
            if not initial["page_images_available"]:
                raise RuntimeError("Install Poppler to verify the original-page preview")
            assert checked(client.get(path + "/pages/1.png")).content.startswith(b"\x89PNG\r\n\x1a\n")
            reviewed = checked(client.post(path + "/review", json={
                "field": "title", "action": "confirm", "revision": 0,
                "reviewer": "Automated clean source QA - not gold",
            }, headers={"X-Skony-Token": initial["csrf_token"]})).json()
            assert reviewed["revision"] == 1
            assert client.post(path + "/extract", content=b"{}",
                               headers={"X-Skony-Token": initial["csrf_token"]}).status_code == 409
        with running(package, state, directory / "second.log") as client:
            restarted = checked(client.get("/api/state")).json()
            assert len(restarted["documents"]) == 1
            assert restarted["documents"][0]["id"] == identifier
            exported = checked(client.get(path + "/export")).json()
            assert len(exported["fields"]) == 1 and len(exported["unreviewed_fields"]) == 7
            assert exported["source"]["synthetic"] is True
            assert len(checked(client.get(path + "/audit")).json()) == 1
        print(json.dumps({"clean_source_start": "passed", "credentials": "not required",
                          "private_pilot": "not copied", "pdf_preview": "passed",
                          "review_survives_restart": "passed", "live_extraction": "blocked in replay",
                          "docker_execution": "not tested by this script"}, indent=2))


if __name__ == "__main__":
    main()
