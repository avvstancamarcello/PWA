import ipaddress
import json
import socket
import urllib.parse

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.util.connection import create_connection

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
ALLOWED_PORTS = {None, 80, 443}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
SW_KEYWORDS = ("serviceworker.register", "navigator.serviceworker")

app = FastAPI(
    title="PWA Detector API",
    description="Microservizio per verificare la struttura PWA di una pagina web.",
    version="2.1.0",
)

# Origine globale: le credenziali devono restare disabilitate.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class PWAResponse(BaseModel):
    url: str
    is_pwa: bool
    manifest_tag_found: bool
    manifest_file_valid: bool
    service_worker_detected: bool


def resolve_public_ip(url: str) -> str | None:
    """Anti-SSRF: schema http(s), porte web e TUTTI gli IP risolti devono essere pubblici.

    Restituisce l'IP validato (da usare per il pinning) oppure None.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.port not in ALLOWED_PORTS:
            return None
        infos = socket.getaddrinfo(parsed.hostname, None)
        ips = [info[4][0] for info in infos]
        if not ips or not all(ipaddress.ip_address(ip).is_global for ip in ips):
            return None
        return ips[0]
    except (socket.gaierror, ValueError, UnicodeError):
        return None


class PinnedAdapter(HTTPAdapter):
    """Connette sempre all'IP già validato (anti DNS rebinding).

    Host header, SNI e verifica del certificato restano sul nome originale.
    """

    def __init__(self, ip: str):
        self._ip = ip
        super().__init__()

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        ip = self._ip

        def pinned_new_conn(conn):
            return create_connection(
                (ip, conn.port),
                conn.timeout,
                source_address=conn.source_address,
                socket_options=conn.socket_options,
            )

        class PinnedHTTPConnection(HTTPConnection):
            def _new_conn(self):
                return pinned_new_conn(self)

        class PinnedHTTPSConnection(HTTPSConnection):
            def _new_conn(self):
                return pinned_new_conn(self)

        class PinnedHTTPPool(HTTPConnectionPool):
            ConnectionCls = PinnedHTTPConnection

        class PinnedHTTPSPool(HTTPSConnectionPool):
            ConnectionCls = PinnedHTTPSConnection

        self.poolmanager.pool_classes_by_scheme = {
            "http": PinnedHTTPPool,
            "https": PinnedHTTPSPool,
        }


def safe_get(url: str, max_bytes: int = MAX_BYTES) -> tuple[str, str]:
    """GET con IP pinning, redirect gestiti a mano (ogni hop è validato) e limite di dimensione.

    Restituisce (url_finale, testo).
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        ip = resolve_public_ip(current)
        if ip is None:
            raise HTTPException(
                status_code=403,
                detail="Accesso negato: URL non valido o diretto a rete non pubblica.",
            )
        try:
            with requests.Session() as session:
                # Ignora i proxy d'ambiente: eluderebbero il pinning dell'IP
                session.trust_env = False
                adapter = PinnedAdapter(ip)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                with session.get(
                    current,
                    headers=HEADERS,
                    timeout=(4, 8),
                    stream=True,
                    allow_redirects=False,
                ) as r:
                    if r.status_code in (301, 302, 303, 307, 308):
                        location = r.headers.get("location")
                        if not location:
                            raise HTTPException(status_code=400, detail="Redirect non valido.")
                        current = urllib.parse.urljoin(current, location)
                        continue
                    if r.status_code != 200:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Sito non raggiungibile. HTTP Status: {r.status_code}",
                        )
                    cl = r.headers.get("content-length")
                    if cl and cl.isdigit() and int(cl) > max_bytes:
                        raise HTTPException(status_code=413, detail="Risposta troppo grande.")
                    data = bytearray()
                    for chunk in r.iter_content(chunk_size=8192):
                        data.extend(chunk)
                        if len(data) > max_bytes:
                            raise HTTPException(status_code=413, detail="Risposta troppo grande.")
                    return current, data.decode(r.encoding or "utf-8", errors="replace")
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Errore di rete: {e}")
    raise HTTPException(status_code=400, detail="Troppi redirect.")


def find_manifest_href(soup: BeautifulSoup):
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        if isinstance(rel, str):
            rel = rel.split()
        if "manifest" in (r.lower() for r in rel) and link.get("href"):
            return link["href"]
    return None


def manifest_is_valid(manifest_url: str) -> bool:
    try:
        _, text = safe_get(manifest_url)
        data = json.loads(text)
    except (HTTPException, ValueError):
        return False
    return isinstance(data, dict) and ("start_url" in data or "short_name" in data or "name" in data)


def detect_service_worker(soup: BeautifulSoup) -> bool:
    """Cerca la registrazione solo negli script inline (gli script esterni non sono scaricati)."""
    for script in soup.find_all("script"):
        text = (script.string or script.get_text() or "").lower()
        if any(kw in text for kw in SW_KEYWORDS):
            return True
    return False


@app.get("/api/v1/check-pwa", response_model=PWAResponse)
def check_pwa(url: str = Query(..., max_length=2048, description="URL da scansionare")):
    clean_url = url.strip()
    if "://" not in clean_url:
        clean_url = "https://" + clean_url

    final_url, html = safe_get(clean_url)
    soup = BeautifulSoup(html, "html.parser")

    href = find_manifest_href(soup)
    manifest_tag_found = href is not None
    manifest_file_valid = False
    if href:
        manifest_file_valid = manifest_is_valid(urllib.parse.urljoin(final_url, href))

    service_worker_detected = detect_service_worker(soup)

    # Il manifest valido (trovato tramite il tag) è condizione necessaria e sufficiente.
    is_pwa = manifest_file_valid

    return PWAResponse(
        url=final_url,
        is_pwa=is_pwa,
        manifest_tag_found=manifest_tag_found,
        manifest_file_valid=manifest_file_valid,
        service_worker_detected=service_worker_detected,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
