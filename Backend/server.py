import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .api import API
from .config import FRONTEND_ROOT, HOST, PORT, PROJECT_ROOT
from .database import initialize


class Handler(BaseHTTPRequestHandler):
    server_version = "PythonProject/1.0"

    def respond(self, data, status=200, cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", f"updraft_uid={cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000: raise ValueError("Request body too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def route(self): API(self).dispatch()
    do_GET = route
    do_POST = route
    do_PATCH = route
    do_PUT = route

    def serve_frontend(self, url_path):
        relative = "index.html" if url_path in ("", "/") else url_path.lstrip("/")
        # Support both /pages/... and /Frontend/pages/... URLs so the existing
        # relative frontend links and the screenshot folder layout both work.
        if relative.startswith("Frontend/"):
            target = (PROJECT_ROOT / relative).resolve()
            if not target.is_file():
                target = (FRONTEND_ROOT / relative[len("Frontend/"):]).resolve()
                if not target.is_file(): target = (PROJECT_ROOT / relative[len("Frontend/"):]).resolve()
        else:
            target = (FRONTEND_ROOT / relative).resolve()
            if not target.is_file(): target = (PROJECT_ROOT / relative).resolve()
        if FRONTEND_ROOT not in target.parents and target != FRONTEND_ROOT and PROJECT_ROOT not in target.parents:
            return self.respond({"error": "Not found."}, 404)
        if target.is_dir(): target = target / "index.html"
        if not target.is_file(): return self.respond({"error": "Not found."}, 404)
        content = target.read_bytes()
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", kind + ("; charset=utf-8" if kind.startswith(("text/", "application/javascript")) else ""))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt, *args): print("%s - %s" % (self.address_string(), fmt % args))


def main():
    initialize()
    print(f"Backend running at http://{HOST}:{PORT}")
    print(f"Frontend available at http://{HOST}:{PORT}/")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__": main()
