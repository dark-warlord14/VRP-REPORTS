"""Simple HTTP server for the VRP dashboard."""

import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from vrp.config import DATA_DIR, UI_DIR
from vrp.utils import logger


class VRPHandler(SimpleHTTPRequestHandler):
    """Serve UI files and data with proper MIME types and CORS."""

    def do_GET(self):
        # Strip query string before routing
        path = self.path.split("?", 1)[0]

        # Route /data/* to data directory
        if path.startswith("/data/"):
            rel = path[6:]  # strip /data/
            filepath = DATA_DIR / rel
        elif path == "/" or path == "":
            filepath = UI_DIR / "index.html"
        else:
            # Strip leading slash
            rel = path.lstrip("/")
            filepath = UI_DIR / rel

        filepath = filepath.resolve()
        ui_root = UI_DIR.resolve()
        data_root = DATA_DIR.resolve()

        # Security: prevent path traversal using is_relative_to (Python 3.9+)
        if not (
            filepath.is_relative_to(ui_root)
            or filepath.is_relative_to(data_root)
        ):
            self.send_error(403, "Forbidden")
            return

        if not filepath.exists() or not filepath.is_file():
            # SPA fallback: serve index.html for non-file routes
            filepath = UI_DIR / "index.html"
            if not filepath.exists():
                self.send_error(404, "Not Found")
                return

        # Determine MIME type
        mime, _ = mimetypes.guess_type(str(filepath))
        if mime is None:
            mime = "application/octet-stream"
        # Fix common types
        ext = filepath.suffix.lower()
        mime_overrides = {
            ".json": "application/json",
            ".md": "text/markdown; charset=utf-8",
            ".js": "application/javascript",
            ".css": "text/css",
            ".html": "text/html; charset=utf-8",
            ".svg": "image/svg+xml",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".diff": "text/plain; charset=utf-8",
            ".patch": "text/plain; charset=utf-8",
        }
        mime = mime_overrides.get(ext, mime)

        try:
            file_size = filepath.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            _CHUNK = 8192
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(_CHUNK)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        # Suppress default logging, use our logger
        pass


def run_server(port: int = 8080):
    """Start the VRP dashboard server (binds to localhost only)."""
    server = ThreadingHTTPServer(("127.0.0.1", port), VRPHandler)
    logger.info(f"Dashboard: http://localhost:{port}")
    logger.info("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.server_close()
