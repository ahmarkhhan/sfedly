"""Verify the container, PDF preview and review persistence in a disposable Compose project.

Uses no credentials or private PDFs. Removes only its uniquely named QA project
and QA volume on exit. Writes a machine-readable report even if Docker is absent.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def checked(response):
    response.raise_for_status()
    return response


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/docker-check")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "docker_execution": "unavailable", "checks": {}}
    docker = shutil.which("docker")
    log_path = args.out / "docker.log"
    report_path = args.out / "report.json"
    result = 2
    try:
        if not docker:
            report["reason"] = "Docker CLI is not installed or not on PATH; no container was built or run."
            return result
        environment = dict(os.environ)
        environment.update(SKONY_MODE="replay", LLM_API_KEY="", LLM_NAME="swiss-ai/Apertus-v1.5-70B",
                           LLM_BASE_URL="https://api.inference.cscs.ch/v1")
        probe = subprocess.run([docker, "info", "--format", "{{json .ServerVersion}}"],
                               capture_output=True, text=True, env=environment, timeout=20)
        if probe.returncode:
            report["reason"] = "Docker daemon is unavailable; start a Linux container engine and rerun."
            return result
        report["engine_version"] = json.loads(probe.stdout)
        with socket.socket() as probe_socket:
            probe_socket.bind(("127.0.0.1", 0))
            port = probe_socket.getsockname()[1]
        environment["SKONY_PORT"] = str(port)
        project = "skony-qa-" + uuid.uuid4().hex[:16]
        report["project"] = project
        with tempfile.TemporaryDirectory(prefix="skony-docker-check-") as temporary, log_path.open("w", encoding="utf-8") as log:
            env_file = Path(temporary) / "empty.env"
            env_file.write_text("", encoding="utf-8")
            command = [docker, "compose", "--project-name", project, "--env-file", str(env_file),
                       "--file", str(ROOT / "compose.yaml")]

            def compose(*arguments, timeout=1800, capture=False):
                process = subprocess.run([*command, *arguments], cwd=ROOT, env=environment,
                    stdout=subprocess.PIPE if capture else log, stderr=log, text=True, timeout=timeout)
                if process.returncode:
                    raise RuntimeError("Docker command failed; inspect the local docker.log")
                return process.stdout

            try:
                compose("build", "workbench")
                report["checks"]["image_build"] = "passed"
                compose("run", "--rm", "--no-deps", "-e", "LLM_API_KEY=", "workbench",
                        "python", "-m", "unittest", "discover", "-s", "tests")
                report["checks"]["container_tests"] = "passed"
                compose("up", "--detach", "--wait", "--wait-timeout", "90", timeout=120)
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=40) as client:
                    assert checked(client.get("/healthz")).json() == {"status": "ok", "mode": "replay"}
                    state = checked(client.get("/api/state")).json()
                    assert not state["api_configured"] and len(state["documents"]) == 1
                    identifier = state["documents"][0]["id"]
                    path = f"/api/documents/{identifier}"
                    document = checked(client.get(path)).json()
                    assert document["source"]["synthetic"] and not document["source"]["gold_annotation"]
                    assert checked(client.get(path + "/pdf")).content.startswith(b"%PDF-")
                    assert checked(client.get(path + "/pages/1.png")).content.startswith(b"\x89PNG\r\n\x1a\n")
                    report["checks"]["health_pdf_and_image_preview"] = "passed"
                    reviewed = checked(client.post(path + "/review", json={"field": "title", "action": "confirm",
                        "revision": document["revision"], "reviewer": "Automated Docker QA - not gold"},
                        headers={"X-Skony-Token": state["csrf_token"]})).json()
                    assert reviewed["fields"]["title"]["review"] is not None
                    assert client.post(path + "/extract", content=b"{}",
                        headers={"X-Skony-Token": state["csrf_token"]}).status_code == 409
                compose("exec", "-T", "workbench", "python", "-c",
                    "import os; from pathlib import Path; assert os.getuid() != 0; "
                    "assert not os.environ.get('LLM_API_KEY'); "
                    "assert not any(Path(p).exists() for p in ['/app/.env', '/app/data/private', '/app/output'])")
                report["checks"]["nonroot_public_only_runtime"] = "passed"
                compose("build", "workbench")
                compose("up", "--detach", "--force-recreate", "--wait", "--wait-timeout", "90", timeout=120)
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=40) as client:
                    exported = checked(client.get(path + "/export")).json()
                    assert exported["document_sha256"] == document["document"]["sha256"]
                    assert len(exported["fields"]) == 1 and len(exported["unreviewed_fields"]) == 7
                    assert len(checked(client.get(path + "/audit")).json()) == 1
                report["checks"]["review_survives_rebuild_and_recreate"] = "passed"
                report["docker_execution"] = "passed"
                result = 0
            finally:
                # The random project name was created above by this invocation.
                # This command cannot target the user's normal Compose project.
                try:
                    compose("down", "--volumes", "--remove-orphans", timeout=90)
                    report["checks"]["disposable_project_cleanup"] = "passed"
                except (RuntimeError, subprocess.SubprocessError):
                    report["checks"]["disposable_project_cleanup"] = "failed"
                    raise
    except (OSError, ValueError, AssertionError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(docker_execution="failed", reason=type(error).__name__ + ": inspect local docker.log")
        result = 1
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        print(f"Report: {report_path}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
