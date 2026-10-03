"""HTTP server (design C10): stdlib ``ThreadingHTTPServer``, routes are a dict.

``ThreadingHTTPServer`` rather than ``HTTPServer``, because held-open SSE
connections (M2) would otherwise wedge the server on the second client.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import sys
from dataclasses import dataclass, field
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, BinaryIO, Callable
from urllib.parse import parse_qs, urlsplit

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_JSON_BYTES = 64 * 1024
# Every state-changing request must carry this header. Browsers will not send a
# custom header cross-origin without a CORS preflight, which this server never
# grants, so a page elsewhere cannot drive the admin API.
CSRF_HEADER = "X-Tower-Request"


class HttpError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: Any  # email.message.Message
    body: BinaryIO
    client: str

    @property
    def content_length(self) -> int:
        try:
            n = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise HttpError(HTTPStatus.LENGTH_REQUIRED, "Content-Length required") from None
        if n < 0:
            raise HttpError(HTTPStatus.BAD_REQUEST, "bad Content-Length")
        return n

    def json(self) -> Any:
        n = self.content_length
        if n > MAX_JSON_BYTES:
            raise HttpError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body too large")
        try:
            return json.loads(self.body.read(n) or b"{}")
        except json.JSONDecodeError:
            raise HttpError(HTTPStatus.BAD_REQUEST, "invalid JSON") from None

    def cookie(self, name: str) -> str | None:
        jar = SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except Exception:  # noqa: BLE001 — a malformed cookie is just no cookie
            return None
        morsel = jar.get(name)
        return morsel.value if morsel else None


@dataclass
class Response:
    status: int = 200
    body: bytes = b""
    content_type: str = "text/plain; charset=utf-8"
    headers: list[tuple[str, str]] = field(default_factory=list)
    # Set for a long-lived response (SSE): called with a write function after the
    # headers, and the connection closes when it returns.
    stream: Callable[[Callable[[bytes], None]], None] | None = None


def json_response(obj: Any, status: int = 200, headers: list[tuple[str, str]] | None = None) -> Response:
    return Response(status, json.dumps(obj).encode(), "application/json", headers or [])


Route = Callable[[Request], Response]
Routes = dict[tuple[str, str], Route]


def make_server(routes: Routes, host: str, port: int, static_dir: Path = STATIC_DIR) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "tower"
        protocol_version = "HTTP/1.1"
        timeout = 60  # a stalled client cannot hold a thread forever

        def do_GET(self) -> None:
            self._handle("GET")

        def do_POST(self) -> None:
            self._handle("POST")

        def _handle(self, method: str) -> None:
            url = urlsplit(self.path)
            req = Request(method, url.path, parse_qs(url.query), self.headers, self.rfile,
                          self.client_address[0])
            try:
                if method == "POST" and self.headers.get(CSRF_HEADER) != "1":
                    raise HttpError(HTTPStatus.FORBIDDEN, f"missing {CSRF_HEADER} header")
                route = routes.get((method, url.path))
                if route is not None:
                    resp = route(req)
                elif method == "GET":
                    resp = _static(static_dir, url.path)
                elif any(path == url.path for _, path in routes):
                    raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
                else:
                    raise HttpError(HTTPStatus.NOT_FOUND, "not found")
            except HttpError as e:
                resp = json_response({"error": e.message}, e.status)
            except Exception:  # noqa: BLE001 — never kill the server thread
                log.exception("error handling %s %s", method, url.path)
                resp = json_response({"error": "internal error"}, 500)
            self._send(resp)

        def _send(self, resp: Response) -> None:
            if resp.stream is not None:
                self._send_stream(resp)
                return
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Content-Length", str(len(resp.body)))
            self.send_header("Cache-Control", "no-cache")
            for k, v in resp.headers:
                self.send_header(k, v)
            # A request body we did not read would be parsed as the next request.
            if resp.status >= 400:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            self.wfile.write(resp.body)

        def _send_stream(self, resp: Response) -> None:
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            for k, v in resp.headers:
                self.send_header(k, v)
            self.end_headers()
            self.close_connection = True

            def write(data: bytes) -> None:
                self.wfile.write(data)
                self.wfile.flush()

            assert resp.stream is not None
            resp.stream(write)

        def log_message(self, format: str, *args: Any) -> None:
            log.debug("%s %s", self.address_string(), format % args)

    server = _Server((host, port), Handler)
    server.daemon_threads = True
    return server


class _Server(ThreadingHTTPServer):
    def handle_error(self, request: Any, client_address: Any) -> None:
        # Phones drop off the AP mid-request all the time; that is not an error.
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            log.debug("client %s went away", client_address[0])
            return
        log.exception("error serving %s", client_address[0])


def _static(root: Path, path: str) -> Response:
    root = root.resolve()
    rel = "index.html" if path in ("", "/") else path.lstrip("/")
    target = (root / rel).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HttpError(HTTPStatus.NOT_FOUND, "not found")
    ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "image/svg+xml"):
        ctype += "; charset=utf-8"
    return Response(200, target.read_bytes(), ctype)
