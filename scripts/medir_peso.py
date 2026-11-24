#!/usr/bin/env python3
"""Mide peso (bytes transferidos, con gzip) y tiempo de cada página y de sus recursos propios (img, css, js; sin video).

Uso: python3 scripts/medir_peso.py http://127.0.0.1:8774 [/ /reservas/ ...]
Una petición por URL; no es una prueba de carga. Fuentes de Google externas no se cuentan (se listan aparte).
"""
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.r = []

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("img", "script", "source") and a.get("src"):
            self.r.append(a["src"])
        if tag == "link" and a.get("href") and a.get("rel") in ("stylesheet", "icon", "preload"):
            self.r.append(a["href"])
        if tag == "video" and a.get("poster"):
            self.r.append(a["poster"])


def get(url):
    t = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        cuerpo = r.read()
        return len(cuerpo), time.time() - t, r.headers


def main():
    base = sys.argv[1].rstrip("/")
    paginas = sys.argv[2:] or ["/", "/reservas/", "/club/", "/escuela/", "/torneos/", "/eventos/", "/galeria/", "/contacto/"]
    for pag in paginas:
        n, seg, h = get(base + pag)
        import gzip, io
        html = urllib.request.urlopen(urllib.request.Request(base + pag, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        p = P(); p.feed(html.decode("utf-8", "replace"))
        total, externos, cuantos = n, [], 1
        for src in dict.fromkeys(p.r):
            u = urllib.parse.urljoin(base + pag, src)
            if urllib.parse.urlparse(u).netloc != urllib.parse.urlparse(base).netloc:
                externos.append(urllib.parse.urlparse(u).netloc)
                continue
            try:
                total += get(u)[0]; cuantos += 1
            except Exception:
                pass
        print(f"{pag:22} html {n/1024:6.1f} KB ({seg*1000:5.0f} ms) · recursos propios {cuantos-1:2d} · total {total/1024:7.1f} KB · externos: {sorted(set(externos)) or '-'}")


main()
