"""Local-only static fixture server; emulate the firmware's /luci-static path."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        if path.startswith("/luci-static/"):
            path = "/package/luci-theme-neobird/htdocs" + path
        return super().translate_path(path)


ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8876"))), Handler).serve_forever()
