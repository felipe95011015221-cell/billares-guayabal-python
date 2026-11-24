#!/usr/bin/env python3
"""Rastrea un sitio y reporta enlaces rotos (internos y externos), imágenes, scripts y hojas de estilo.

Uso:  python3 scripts/verificar_enlaces.py http://127.0.0.1:8774 [--externos] [--max 150] [--pausa 0.1]
Solo biblioteca estándar. Peticiones normales y pocas: una por URL única, con pausa entre ellas.
Sale con código 1 si encuentra enlaces rotos.
"""
import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; VerificadorEnlaces/1.0)"
# Servicios que bloquean clientes automáticos: un 403/429/999 no significa enlace roto.
BLOQUEAN_BOTS = ("unsplash.com", "pexels.com", "instagram.com", "facebook.com", "wa.me", "whatsapp.com", "google.com/maps", "linkedin.com", "tiktok.com")


class Recolector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces, self.recursos, self.ids = [], [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.enlaces.append(a["href"])
        elif tag in ("img", "script", "source", "video", "iframe") and a.get("src"):
            self.recursos.append(a["src"])
        elif tag == "link" and a.get("href") and a.get("rel", "") in ("stylesheet", "icon", "apple-touch-icon", "preload"):
            self.recursos.append(a["href"])
        if tag == "video" and a.get("poster"):
            self.recursos.append(a["poster"])
        if a.get("srcset"):
            self.recursos += [p.strip().split(" ")[0] for p in a["srcset"].split(",") if p.strip()]


def pedir(url, metodo="GET", tiempo=15):
    req = urllib.request.Request(url, method=metodo, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=tiempo) as r:
            cuerpo = r.read(2_000_000) if metodo == "GET" else b""
            return r.status, r.headers, cuerpo
    except urllib.error.HTTPError as e:
        return e.code, e.headers, b""
    except Exception as e:  # noqa: BLE001
        return f"ERROR {type(e).__name__}: {e}", {}, b""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--externos", action="store_true", help="comprobar también enlaces a otros dominios")
    ap.add_argument("--max", type=int, default=150, help="máximo de páginas internas a rastrear")
    ap.add_argument("--pausa", type=float, default=0.1)
    args = ap.parse_args()
    base = args.base.rstrip("/")
    host = urllib.parse.urlparse(base).netloc

    por_ver, vistas, estado, origen, anclas = [base + "/"], set(), {}, {}, []
    paginas_ids = {}
    while por_ver and len(vistas) < args.max:
        url = por_ver.pop(0)
        if url in vistas:
            continue
        vistas.add(url)
        code, hdr, cuerpo = pedir(url)
        estado[url] = code
        time.sleep(args.pausa)
        if code != 200 or "html" not in str(hdr.get("Content-Type", "")):
            continue
        p = Recolector()
        p.feed(cuerpo.decode("utf-8", "replace"))
        paginas_ids[url] = p.ids
        for href in p.enlaces + p.recursos:
            if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            if href.startswith("#"):
                if len(href) > 1:
                    anclas.append((url, href[1:]))
                continue
            absoluta, frag = urllib.parse.urldefrag(urllib.parse.urljoin(url, href))
            origen.setdefault(absoluta, url)
            if urllib.parse.urlparse(absoluta).netloc == host:
                if absoluta in p.recursos or href in p.recursos:
                    pass
                if absoluta not in vistas and absoluta not in por_ver and not absoluta.split("?")[0].endswith((".webp", ".png", ".jpg", ".mp4", ".css", ".js", ".woff2", ".svg", ".ico", ".xml")) \
                        and "/admin" not in absoluta:
                    por_ver.append(absoluta)

    # Recursos internos y externos (una sola petición por URL)
    pendientes = [u for u in origen if u not in estado]
    for u in pendientes:
        interno = urllib.parse.urlparse(u).netloc == host
        if not interno and not args.externos:
            continue
        code, _, _ = pedir(u, "HEAD")
        if code in (403, 405, 501) or isinstance(code, str):
            code, _, _ = pedir(u, "GET")
        estado[u] = code
        time.sleep(args.pausa)

    rotos, avisos = [], []
    for u, c in estado.items():
        if isinstance(c, int) and c < 400:
            continue
        externo_bloqueado = any(b in u for b in BLOQUEAN_BOTS) and isinstance(c, int) and 400 <= c < 500
        (avisos if externo_bloqueado else rotos).append((u, c, origen.get(u, "(inicio)")))
    for pagina, ancla in anclas:
        if ancla not in paginas_ids.get(pagina, {ancla}):
            rotos.append((f"{pagina}#{ancla}", "ancla inexistente", pagina))

    print(f"Páginas rastreadas: {len(vistas)} · URLs comprobadas: {len(estado)} · externos: {'sí' if args.externos else 'no'}")
    for u, c, o in avisos:
        print(f"  AVISO  {c}  {u}   (bloquea clientes automáticos; verificar a mano)  ← {o}")
    for u, c, o in rotos:
        print(f"  ROTO   {c}  {u}   ← {o}")
    print("Sin enlaces rotos." if not rotos else f"{len(rotos)} enlace(s) roto(s).")
    return 1 if rotos else 0


if __name__ == "__main__":
    sys.exit(main())
