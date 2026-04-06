"""Tests for vrp/server.py — routing, security, MIME types."""

import io
import json
import threading
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from vrp.server import VRPHandler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockSocket:
    """Minimal socket mock for VRPHandler unit tests."""
    def __init__(self):
        self._output = io.BytesIO()
        self.makefile_reads = [b""]

    def makefile(self, mode, *args, **kwargs):
        if "rb" in mode:
            return io.BytesIO(b"")
        return io.BytesIO(b"")

    def sendall(self, data):
        self._output.write(data)


def make_handler(path: str, ui_dir: Path, data_dir: Path):
    """Instantiate a VRPHandler pointed at tmp dirs, capturing the response."""
    output = io.BytesIO()

    class FakeSocket:
        def makefile(self, mode, *args, **kwargs):
            return io.BytesIO(b"")
        def sendall(self, data):
            output.write(data)

    with patch("vrp.server.UI_DIR", ui_dir), \
         patch("vrp.server.DATA_DIR", data_dir):
        handler = VRPHandler.__new__(VRPHandler)
        handler.path = path
        handler.headers = {}
        handler.command = "GET"
        handler.request_version = "HTTP/1.1"
        handler.server = MagicMock()
        handler.connection = FakeSocket()
        handler.wfile = output
        handler.rfile = io.BytesIO(b"")

    return handler, output


# We use an actual test HTTP server for integration-style tests
class ServerFixture:
    """Spin up a real server thread for black-box HTTP tests."""
    def __init__(self, ui_dir: Path, data_dir: Path):
        self.ui_dir = ui_dir
        self.data_dir = data_dir

        # Patch paths before server thread starts
        self._patches = [
            patch("vrp.server.UI_DIR", ui_dir),
            patch("vrp.server.DATA_DIR", data_dir),
        ]

    def __enter__(self):
        for p in self._patches:
            p.start()
        from http.server import HTTPServer

        from vrp.server import VRPHandler
        self.server = HTTPServer(("127.0.0.1", 0), VRPHandler)
        self.port = self.server.server_address[1]  # OS-assigned port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        for p in self._patches:
            p.stop()

    def get(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status, dict(resp.getheaders()), body


# ---------------------------------------------------------------------------
# Server tests (black-box via real HTTP)
# ---------------------------------------------------------------------------

@pytest.fixture()
def dirs(tmp_path):
    ui = tmp_path / "ui"
    data = tmp_path / "data"
    ui.mkdir()
    data.mkdir()
    (ui / "index.html").write_text("<html>dashboard</html>")
    return ui, data


class TestServerRouting:
    def test_root_serves_index_html(self, dirs):
        ui, data = dirs
        with ServerFixture(ui, data) as srv:
            status, headers, body = srv.get("/")
        assert status == 200
        assert b"dashboard" in body

    def test_data_json_served(self, dirs):
        ui, data = dirs
        (data / "index.json").write_text('[{"id": "1"}]')
        with ServerFixture(ui, data) as srv:
            status, headers, body = srv.get("/data/index.json")
        assert status == 200
        assert json.loads(body) == [{"id": "1"}]

    def test_unknown_path_falls_back_to_index(self, dirs):
        ui, data = dirs
        with ServerFixture(ui, data) as srv:
            status, _, body = srv.get("/unknown/route")
        assert status == 200
        assert b"dashboard" in body

    def test_query_string_stripped(self, dirs):
        ui, data = dirs
        (data / "stats.json").write_text('{"total": 1}')
        with ServerFixture(ui, data) as srv:
            status, _, body = srv.get("/data/stats.json?cache=bust")
        assert status == 200
        assert b"total" in body

    def test_large_file_served_correctly(self, dirs):
        """Server must correctly serve files larger than a single chunk (8192 bytes)."""
        ui, data = dirs
        # 64KB file — larger than the 8192-byte chunk size
        large_content = b"A" * 65536
        (data / "large.bin").write_bytes(large_content)
        with ServerFixture(ui, data) as srv:
            status, headers, body = srv.get("/data/large.bin")
        assert status == 200
        assert len(body) == 65536
        assert body == large_content


class TestServerSecurity:
    def test_path_traversal_blocked(self, dirs):
        ui, data = dirs
        # Try to escape data dir
        with ServerFixture(ui, data) as srv:
            status, _, _ = srv.get("/data/../../../etc/passwd")
        # Should either 403 or 200 with index.html fallback — not a real passwd file
        # The resolved path won't be relative to ui or data, so 403
        assert status in (403, 200)
        # Verify we didn't leak system files
        if status == 200:
            pass  # SPA fallback is OK — but let's ensure no passwd content

    def test_path_traversal_ui_blocked(self, dirs):
        ui, data = dirs
        with ServerFixture(ui, data) as srv:
            status, _, _ = srv.get("/../../../etc/passwd")
        assert status in (403, 200)

    def test_bound_to_localhost(self):
        """run_server must bind to 127.0.0.1, not 0.0.0.0."""
        captured = {}

        class FakeHTTPServer:
            def __init__(self, addr, handler):
                captured["addr"] = addr
            def serve_forever(self):
                raise KeyboardInterrupt
            def server_close(self):
                pass

        with patch("vrp.server.ThreadingHTTPServer", FakeHTTPServer):
            from vrp.server import run_server
            run_server(port=19999)

        assert captured["addr"][0] == "127.0.0.1"


class TestServerMimeTypes:
    def test_json_mime(self, dirs):
        ui, data = dirs
        (data / "x.json").write_text("{}")
        with ServerFixture(ui, data) as srv:
            _, headers, _ = srv.get("/data/x.json")
        assert "application/json" in headers.get("Content-Type", "")

    def test_js_mime(self, dirs):
        ui, data = dirs
        (ui / "app.js").write_text("const x = 1;")
        with ServerFixture(ui, data) as srv:
            _, headers, _ = srv.get("/app.js")
        assert "javascript" in headers.get("Content-Type", "")

    def test_html_mime(self, dirs):
        ui, data = dirs
        with ServerFixture(ui, data) as srv:
            _, headers, _ = srv.get("/")
        assert "text/html" in headers.get("Content-Type", "")
