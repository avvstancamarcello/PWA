import socket
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import app as engine

client = TestClient(engine.app)

PWA_HTML = """<html><head><link rel="manifest" href="/m.json"></head>
<body><script>navigator.serviceWorker.register('/sw.js')</script></body></html>"""


def fake_getaddrinfo(host, port, *a, **k):
    ips = {"public.test": "93.184.216.34", "evil.test": "127.0.0.1"}
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ips.get(host, host), port or 0))]


class FakeResp:
    def __init__(self, body="", status=200, headers=None):
        self.status_code = status
        self.headers = headers or {}
        self._body = body.encode()
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"
        self.is_redirect = status in (301, 302, 307, 308)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]


@pytest.fixture(autouse=True)
def net():
    with mock.patch("socket.getaddrinfo", fake_getaddrinfo):
        yield


def route(mapping):
    def _get(self, url, **kw):
        assert kw.get("allow_redirects") is False
        return mapping[url]

    return mock.patch("requests.Session.get", _get)


def test_pwa_true():
    with route({
        "https://public.test": FakeResp(PWA_HTML),
        "https://public.test/m.json": FakeResp('{"short_name": "x"}'),
    }):
        r = client.get("/api/v1/check-pwa", params={"url": "public.test"})
    assert r.status_code == 200
    assert r.json()["is_pwa"] is True
    assert r.json()["service_worker_detected"] is True


def test_no_manifest_not_pwa_even_with_sw_text():
    html = "<script>navigator.serviceWorker.register('/sw.js')</script>"
    with route({"https://public.test": FakeResp(html)}):
        r = client.get("/api/v1/check-pwa", params={"url": "public.test"})
    assert r.json()["is_pwa"] is False
    assert r.json()["service_worker_detected"] is True


def test_register_in_comment_or_text_is_ignored():
    html = "<p>use .register( here</p><!-- navigator.serviceWorker -->"
    with route({"https://public.test": FakeResp(html)}):
        r = client.get("/api/v1/check-pwa", params={"url": "public.test"})
    assert r.json()["service_worker_detected"] is False


@pytest.mark.parametrize("u", ["http://evil.test", "http://127.0.0.1:8000", "http://[::1]/", "ftp://public.test", "https://public.test:22"])
def test_ssrf_blocked(u):
    r = client.get("/api/v1/check-pwa", params={"url": u})
    assert r.status_code == 403


def test_redirect_to_private_blocked():
    with route({"https://public.test": FakeResp("", 302, {"location": "http://evil.test/"})}):
        r = client.get("/api/v1/check-pwa", params={"url": "public.test"})
    assert r.status_code == 403


def test_size_limit():
    with route({"https://public.test": FakeResp("a" * (engine.MAX_BYTES + 10))}):
        r = client.get("/api/v1/check-pwa", params={"url": "public.test"})
    assert r.status_code == 413


def test_cors_no_credentials():
    r = client.get("/api/v1/check-pwa", params={"url": "http://evil.test"}, headers={"Origin": "https://x.it"})
    assert "access-control-allow-credentials" not in r.headers


def test_dns_pinning_connects_to_validated_ip():
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"pinned-ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Host", self.headers["Host"])
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]

    # "pinned.test" non è risolvibile: la richiesta riesce solo se si usa l'IP pinnato.
    with mock.patch.object(engine, "resolve_public_ip", lambda u: "127.0.0.1"), \
         mock.patch.object(engine, "ALLOWED_PORTS", {port}):
        final, text = engine.safe_get(f"http://pinned.test:{port}/")
    srv.shutdown()
    assert text == "pinned-ok"


def test_pinning_ignores_second_dns_answer():
    # Il primo controllo vede un IP pubblico, un eventuale secondo lookup darebbe 127.0.0.1:
    # con il pinning la connessione parte comunque verso l'IP validato (non raggiungibile qui).
    calls = []

    def gai(host, port, *a, **k):
        calls.append(host)
        ip = "93.184.216.34" if len(calls) == 1 else "127.0.0.1"
        return [(socket.AF_INET, 0, 0, "", (ip, 0))]

    with mock.patch("socket.getaddrinfo", gai), \
         mock.patch.object(engine, "create_connection") as cc:
        cc.side_effect = OSError("blocked")
        with pytest.raises(engine.HTTPException):
            engine.safe_get("http://rebind.test")
    assert cc.call_args[0][0][0] == "93.184.216.34"
