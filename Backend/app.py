import json
import mimetypes
from pathlib import Path

from flask import Flask, Response, request

from .api import API
from .config import FRONTEND_ROOT, HOST, PORT, PROJECT_ROOT
from .database import initialize


app = Flask(__name__)
initialize()


class FlaskRequestAdapter:
    """Adapt Flask's request/response objects to the existing API handlers."""

    def __init__(self):
        self.headers = request.headers
        self.path = request.full_path
        self.command = request.method

    def read_json(self):
        if request.content_length and request.content_length > 1_000_000:
            raise ValueError("Request body too large")
        return json.loads(request.get_data(cache=True) or b"{}")

    def respond(self, data, status=200, cookie=None, cookies=None):
        body = json.dumps(data, ensure_ascii=False)
        response = Response(body, status=status, content_type="application/json; charset=utf-8")
        response.headers["Cache-Control"] = "no-store"
        if cookie:
            response.set_cookie(
                "updraft_uid", cookie, path="/", httponly=True,
                samesite="Lax", max_age=31_536_000,
            )
        for value in cookies or []:
            response.headers.add("Set-Cookie", value)
        return response

    def serve_frontend(self, url_path):
        relative = "index.html" if url_path in ("", "/") else url_path.lstrip("/")
        if relative.startswith("Frontend/"):
            target = (PROJECT_ROOT / relative).resolve()
            if not target.is_file():
                target = (FRONTEND_ROOT / relative[len("Frontend/"):]).resolve()
                if not target.is_file():
                    target = (PROJECT_ROOT / relative[len("Frontend/"):]).resolve()
        else:
            target = (FRONTEND_ROOT / relative).resolve()
            if not target.is_file() and relative == "index.html":
                target = (FRONTEND_ROOT / "Index.html").resolve()
            if not target.is_file():
                target = (PROJECT_ROOT / relative).resolve()

        if FRONTEND_ROOT not in target.parents and target != FRONTEND_ROOT and PROJECT_ROOT not in target.parents:
            return self.respond({"error": "Not found."}, 404)
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return self.respond({"error": "Not found."}, 404)

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith(("text/", "application/javascript", "application/json")):
            content_type += "; charset=utf-8"
        return Response(target.read_bytes(), content_type=content_type)


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PATCH", "PUT"])
@app.route("/<path:path>", methods=["GET", "POST", "PATCH", "PUT"])
def dispatch(path):
    return API(FlaskRequestAdapter()).dispatch()


def main():
    initialize()
    print(f"Flask backend running at http://{HOST}:{PORT}")
    print(f"Frontend available at http://{HOST}:{PORT}/")
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    main()
