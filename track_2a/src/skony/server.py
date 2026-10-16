"""Local review workbench with an explicit replay/live execution mode."""

import json
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from pydantic import ValidationError
from pypdf.errors import PdfReadError

from .client import Settings, complete
from .pdf import read_pdf
from .pdf_evidence import passage_regions
from .pipeline import messages_for, verify_response
from .review import ReviewAction, ReviewError, ReviewStore
from .schema import CandidateExtraction, Document, ExtractionResult
from .explorer import Explorer

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "web"


class Workbench:
    def __init__(self, directory: Path, *, seed_pilot=True, mode="replay", public_port=None):
        if mode not in {"replay", "live"}:
            raise ValueError("Choose replay or live mode")
        if public_port is not None and not 1 <= public_port <= 65535:
            raise ValueError("Invalid public port")
        self.mode = mode
        self.public_port = public_port
        self.store = ReviewStore(directory)
        self.token = secrets.token_urlsafe(32)
        self.render_lock = threading.Lock()
        self.pdf_evidence_lock = threading.Lock()
        self.model_lock = threading.Lock()
        self.v2_lock = threading.Lock()
        self._v2 = None
        # A process interrupted during inference cannot leave a permanent running badge.
        with self.store.db(write=True) as db:
            db.execute("UPDATE documents SET extraction_state='failed',extraction_error='The previous extraction was interrupted. You can run it again.' WHERE extraction_state='running'")
        if seed_pilot:
            if mode == "replay":
                from .demo import load_demo
                pdf, result, source = load_demo()
                self.store.add(result.document, pdf, source, result)
            else:
                self.seed_pilot()

    def settings(self):
        return Settings.from_environment()

    def versioned_api(self):
        # The first explicit v2 request performs the backed-up additive migration.
        # Ordinary v1 reads retain their compatibility behavior.
        with self.v2_lock:
            if self._v2 is None:
                from .api_v2 import V2API
                self._v2 = V2API(self.store)
            return self._v2

    def seed_pilot(self):
        result_path = ROOT / "output" / "live_pilot" / "nidau-70b-v02" / "result-evidence-v02.json"
        pdf_path = ROOT / "data" / "private" / "nidau-postulate-2013.pdf"
        manifest = ROOT / "data" / "private" / "pilot_source_manifest.json"
        if result_path.is_file() and pdf_path.is_file():
            result = ExtractionResult.model_validate_json(result_path.read_text(encoding="utf-8"))
            source = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
            source.update({"body_label": "Nidau · Municipal", "language_label": "German", "recorded_pilot": True})
            self.store.add(result.document, pdf_path, source, result)

    def state(self):
        configured, model = False, None
        if self.mode == "live":
            try:
                settings = self.settings()
                configured, model = bool(settings.api_key), settings.model
            except ValueError:
                pass
        return {"documents": self.store.list(), "csrf_token": self.token, "api_configured": configured,
                "configured_model": model, "mode": self.mode,
                "page_images_available": shutil.which("pdftoppm") is not None}

    def upload(self, contents: bytes, filename: str):
        if not contents.startswith(b"%PDF-"):
            raise ReviewError("Choose a PDF document")
        with tempfile.TemporaryDirectory(dir=self.store.directory) as temporary:
            path = Path(temporary) / "upload.pdf"
            path.write_bytes(contents)
            document = read_pdf(path)
            document.filename = Path(filename.replace("\\", "/")).name[:180] or "document.pdf"
            return self.store.add(document, path, {"body_label": "Uploaded document", "recorded_pilot": False})

    def image(self, identifier: str, page: int):
        item = self.store.get(identifier)
        if page not in {p["number"] for p in item["document"]["pages"]}:
            raise ReviewError("Page not found", 404)
        return self.render_image(self.store.pdf_path(identifier), identifier, page)

    def evidence(self, identifier: str, field: str):
        item = self.store.get(identifier)
        if field not in item["fields"]:
            raise ReviewError("Unknown extraction field", 404)
        value = item["fields"][field]
        effective = value["review"] or value["suggestion"]
        provenance = effective.get("provenance")
        result = {"revision": item["revision"], "field": field,
                  "page": provenance.get("page") if provenance else None,
                  "status": "unavailable", "regions": [],
                  "reason": "No supporting passage is recorded for this field."}
        if not provenance:
            return result
        if provenance.get("basis") == "image":
            result["reason"] = "Human image transcription; no region coordinates were recorded."
            return result
        source = next((p for p in item["document"]["pages"] if p["number"] == provenance["page"]), None)
        start, end = provenance.get("start"), provenance.get("end")
        if (source is None or not isinstance(start, int) or not isinstance(end, int)
                or not 0 <= start < end <= len(source["text"])
                or source["text"][start:end] != provenance["quote"]):
            result["reason"] = "The saved passage no longer matches the source text."
            return result
        # PDF geometry is serialized because the native PDF library is not thread safe.
        with self.pdf_evidence_lock:
            result.update(passage_regions(self.store.pdf_path(identifier), provenance["page"], provenance["quote"]))
        return result

    def image_v2(self, digest: str, page: int):
        api = self.versioned_api()
        artifact = api.artifact(digest)
        if page not in artifact["pages"]:
            raise ReviewError("Page not found", 404)
        return self.render_image(api.artifact_path(digest), digest, page)

    def render_image(self, source: Path, identifier: str, page: int):
        executable = shutil.which("pdftoppm")
        if not executable:
            return self.render_image_pymupdf(source, identifier, page)
        directory = self.store.directory / "rendered" / identifier
        directory.mkdir(parents=True, exist_ok=True)
        # Separate cache from older previews rendered against the media box.
        prefix = directory / f"page-{page}-crop-v1"
        target = prefix.with_suffix(".png")
        with self.render_lock:
            if not target.is_file():
                try:
                    subprocess.run([executable, "-f", str(page), "-l", str(page), "-singlefile", "-cropbox", "-scale-to", "1600",
                                    "-png", str(source), str(prefix)],
                                   capture_output=True, check=True, timeout=35)
                except (subprocess.SubprocessError, OSError):
                    raise ReviewError("The page image could not be rendered. Open the original PDF.", 503) from None
        return target.read_bytes()

    def render_image_pymupdf(self, source: Path, identifier: str, page: int):
        directory = self.store.directory / "rendered" / identifier
        directory.mkdir(parents=True, exist_ok=True)
        prefix = directory / f"page-{page}-crop-v1"
        target = prefix.with_suffix(".png")
        with self.render_lock:
            if not target.is_file():
                try:
                    import pymupdf
                    with pymupdf.open(source) as pdf:
                        if page < 1 or page > len(pdf):
                            raise ReviewError("Page not found", 404)
                        pg = pdf[page - 1]
                        zoom = 1600 / pg.rect.width
                        pix = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                        pix.save(target)
                except ReviewError:
                    raise
                except Exception:
                    raise ReviewError("The page image could not be rendered. Open the original PDF.", 503) from None
        return target.read_bytes()

    def start(self, identifier: str):
        if self.mode == "replay":
            raise ReviewError("Live extraction is disabled in replay mode. Restart in live mode to use Apertus.", 409)
        settings = self.settings()
        if not settings.api_key:
            raise ReviewError("Configure the local Apertus key before extracting")
        if "apertus" not in settings.model.lower() or "1.5" not in settings.model:
            raise ReviewError("Select an Apertus 1.5 model for this workbench")
        item = self.store.get(identifier)
        document = Document.model_validate(item["document"])
        messages = messages_for(document)
        if not self.model_lock.acquire(blocking=False):
            raise ReviewError("Another extraction is running. Wait for it to finish.", 409)
        try:
            self.store.start_extraction(identifier)
        except Exception:
            self.model_lock.release()
            raise
        def worker():
            try:
                started = time.monotonic()
                content, usage = complete(settings, messages, json_schema=CandidateExtraction.model_json_schema())
                result = verify_response(document, content, settings.model, time.monotonic() - started, usage)
                self.store.finish_extraction(identifier, result, content)
            except ValidationError:
                self.store.fail_extraction(identifier, "Apertus returned inconsistent fields. No new suggestions were accepted; existing reviews are preserved.")
            except ValueError:
                self.store.fail_extraction(identifier, "Apertus extraction failed. Check the configured endpoint, model and access, then try again.")
            except Exception:
                self.store.fail_extraction(identifier, "Extraction could not finish. Existing reviews are preserved.")
            finally:
                self.model_lock.release()
        threading.Thread(target=worker, daemon=True).start()


def make_handler(app: Workbench):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Request paths and headers can contain user filenames; don't log them.
            pass

        def send_bytes(self, contents: bytes, mime: str, status=200, *, attachment=None):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(contents)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(contents)

        def json(self, data, status=200, *, attachment=None):
            self.send_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status, attachment=attachment)

        def service_error(self, error):
            versioned = urlsplit(self.path).path.startswith("/api/v2/")
            metadata = ({"reason_code": {404: "not_found", 409: "dependency_or_revision_conflict", 422: "invalid_contract"}.get(error.status, "request_rejected"),
                         "stage": "service", "affected_ids": [], "retryable": error.status == 409} if versioned else {})
            self.json({"error": str(error), **metadata}, error.status)

        def origin_check(self, *, mutation=False):
            ports = {self.server.server_port}
            if app.public_port is not None:
                ports.add(app.public_port)
            allowed = {f"{host}:{port}" for port in ports for host in ("127.0.0.1", "localhost")}
            if self.headers.get("Host") not in allowed:
                raise ReviewError("Unsupported request host", 403)
            if mutation:
                origin = self.headers.get("Origin")
                if origin is not None and origin not in {"http://" + host for host in allowed}:
                    raise ReviewError("Unsupported request origin", 403)
                if self.headers.get("X-Skony-Token") != app.token:
                    raise ReviewError("Reload the workbench before saving", 403)

        def do_GET(self):
            try:
                self.origin_check()
                path = urlsplit(self.path).path
                static = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                          "/style.css": ("style.css", "text/css; charset=utf-8"),
                          "/workspace.css": ("workspace.css", "text/css; charset=utf-8"),
                          "/profile.js": ("profile.js", "text/javascript; charset=utf-8"),
                          "/scoped": ("scoped.html", "text/html; charset=utf-8"),
                          "/scoped.js": ("scoped.js", "text/javascript; charset=utf-8"),
                          "/scoped.css": ("scoped.css", "text/css; charset=utf-8"),
                          "/explore": ("explore.html", "text/html; charset=utf-8"),
                          "/explore.js": ("explore.js", "text/javascript; charset=utf-8"),
                          "/explore.css": ("explore.css", "text/css; charset=utf-8")}
                if path in static:
                    filename, mime = static[path]
                    return self.send_bytes((STATIC / filename).read_bytes(), mime)
                if path == "/healthz":
                    return self.json({"status": "ok", "mode": app.mode})
                if path == "/api/state":
                    return self.json(app.state())
                parts = [unquote(part) for part in path.strip("/").split("/")]
                if parts[:2] == ["api", "explorer"]:
                    query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                    if any(len(v) != 1 for v in query.values()):
                        raise ReviewError("Explorer filters must have a single value")
                    params = {k: v[0] for k, v in query.items()}
                    explorer = Explorer(app.store)
                    if len(parts) == 2:
                        return self.json(explorer.search(params))
                    if parts[2:] == ["export"]:
                        format = params.get("format", "json")
                        if format not in {"json", "csv"}:
                            raise ReviewError("Choose JSON or CSV for a research brief")
                        brief = explorer.brief(params)
                        if format == "csv":
                            return self.send_bytes(explorer.csv(brief), "text/csv; charset=utf-8", attachment="skony-research.csv")
                        return self.json(brief, attachment="skony-research.json")
                    if len(parts) == 4 and parts[2] == "dossiers":
                        if set(params) - {"reviewed_only"}:
                            raise ReviewError("Unknown dossier filter")
                        filters = explorer.filters(params)
                        return self.json(explorer.detail(parts[3], reviewed_only=filters["reviewed_only"]))
                    raise ReviewError("Explorer resource not found", 404)
                if parts[:2] == ["api", "v2"]:
                    if len(parts) == 5 and parts[2] == "artifacts" and parts[4] == "pdf":
                        return self.send_bytes(app.versioned_api().artifact_path(parts[3]).read_bytes(), "application/pdf")
                    if len(parts) == 6 and parts[2] == "artifacts" and parts[4] == "pages" and parts[5].endswith(".png"):
                        return self.send_bytes(app.image_v2(parts[3], int(parts[5][:-4])), "image/png")
                    return self.json(app.versioned_api().get(parts[2:]))
                if len(parts) >= 3 and parts[:2] == ["api", "documents"]:
                    identifier = parts[2]
                    if len(parts) == 3:
                        return self.json(app.store.get(identifier))
                    if parts[3:] == ["pdf"]:
                        return self.send_bytes(app.store.pdf_path(identifier).read_bytes(), "application/pdf")
                    if parts[3:] == ["audit"]:
                        return self.json(app.store.audit(identifier))
                    if parts[3:] == ["export"]:
                        return self.json(app.store.export(identifier), attachment="skony-reviewed.json")
                    if len(parts) == 6 and parts[3] == "fields" and parts[5] == "evidence":
                        return self.json(app.evidence(identifier, parts[4]))
                    if len(parts) == 5 and parts[3] == "pages" and parts[4].endswith(".png"):
                        return self.send_bytes(app.image(identifier, int(parts[4][:-4])), "image/png")
                raise ReviewError("Not found", 404)
            except ReviewError as error:
                self.service_error(error)
            except BrokenPipeError:
                pass
            except (ValueError, OSError):
                self.json({"error": "The requested resource is unavailable"}, 404)

        def do_POST(self):
            try:
                self.origin_check(mutation=True)
                length = int(self.headers.get("Content-Length", "0"))
                path = urlsplit(self.path).path
                limit = (25 * 1024 * 1024 if path == "/api/upload" else
                         2 * 1024 * 1024 if path.startswith("/api/v2/") else 150000)
                if length < 1 or length > limit:
                    raise ReviewError("Request exceeds the allowed input size", 413)
                body = self.rfile.read(length)
                if path == "/api/upload":
                    filename = parse_qs(urlsplit(self.path).query).get("filename", ["document.pdf"])[0]
                    identifier = app.upload(body, filename)
                    return self.json({"id": identifier}, 201)
                parts = [unquote(part) for part in path.strip("/").split("/")]
                if parts[:2] == ["api", "v2"]:
                    return self.json(app.versioned_api().post(parts[2:], json.loads(body)))
                if len(parts) == 4 and parts[:2] == ["api", "documents"]:
                    identifier = parts[2]
                    if parts[3] == "review":
                        action = ReviewAction.model_validate_json(body)
                        return self.json(app.store.review(identifier, action))
                    if parts[3] == "extract":
                        app.start(identifier)
                        return self.json({"started": True}, 202)
                raise ReviewError("Not found", 404)
            except ReviewError as error:
                self.service_error(error)
            except (ValidationError, ValueError, PdfReadError):
                versioned = urlsplit(self.path).path.startswith("/api/v2/")
                self.json({"error": "Check the input document or review fields. No changes were accepted.",
                           **({"reason_code": "invalid_contract", "stage": "validation", "retryable": False}
                              if versioned else {})}, 422 if versioned else 400)
            except Exception:
                self.json({"error": "The operation could not finish. Reload and try again."}, 500)
    return Handler


def run_server(port=8765, directory: Path | None = None, *, host="127.0.0.1", mode="replay", public_port=None):
    default = "workbench-replay" if mode == "replay" else "workbench"
    app = Workbench(directory or ROOT / "output" / default, mode=mode, public_port=public_port)
    server = ThreadingHTTPServer((host, port), make_handler(app))
    print(f"Skony review workbench ({mode}): http://127.0.0.1:{public_port or server.server_port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
