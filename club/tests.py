"""Pruebas: reglas de disponibilidad, protección contra doble reserva, APIs, páginas y panel."""
import json
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import disponibilidad as disp
from .models import Ajustes, Bloqueo, Mesa, Reserva
from .servicios import ErrorNegocio, crear_reserva

B = disp.BOGOTA
REGLAS = disp.Reglas(duraciones=[60, 120], intervalo_min=30, anticipacion_min=60, dias_max=30, hora_apertura=540, hora_cierre=1560)
AHORA = datetime(2026, 11, 23, 12, 0, tzinfo=B)


class ReglasDisponibilidad(TestCase):
    def test_intervalos_contiguos_no_se_solapan(self):
        a = datetime(2026, 11, 25, 10, tzinfo=B)
        self.assertFalse(disp.se_solapan(a, a + timedelta(hours=2), a + timedelta(hours=2), a + timedelta(hours=4)))
        self.assertTrue(disp.se_solapan(a, a + timedelta(hours=2), a + timedelta(hours=1), a + timedelta(hours=3)))

    def test_validar_horario(self):
        manana = date(2026, 11, 24)
        self.assertIsNone(disp.validar_horario(manana, 1200, 120, REGLAS, AHORA))
        self.assertIn("Duración", disp.validar_horario(manana, 1200, 45, REGLAS, AHORA))
        self.assertIn("no válida", disp.validar_horario(manana, 1215, 60, REGLAS, AHORA))
        self.assertIn("fuera", disp.validar_horario(manana, 1500, 120, REGLAS, AHORA))  # termina después de las 2 a. m.
        self.assertIn("anticipación", disp.validar_horario(date(2026, 11, 23), 750, 60, REGLAS, AHORA))  # 12:30, hoy
        self.assertIn("30 días", disp.validar_horario(date(2027, 1, 10), 1200, 60, REGLAS, AHORA))

    def test_cruce_de_medianoche(self):
        ini = disp.instante(date(2026, 11, 24), 1500)  # 1:00 a. m. del 25
        self.assertEqual((ini.day, ini.hour), (25, 1))

    def test_prioridad_de_estados(self):
        mesa = disp.MesaDatos(1, "Mesa 1", "pool", 10000)
        ini = datetime(2026, 11, 25, 20, tzinfo=B)
        fin = ini + timedelta(hours=2)
        r = lambda estado: [disp.Intervalo(1, ini, fin, estado=estado)]  # noqa: E731
        self.assertEqual(disp.estado_mesa(mesa, ini, fin, [], []), "disponible")
        self.assertEqual(disp.estado_mesa(mesa, ini, fin, r("pendiente"), []), "pendiente")
        self.assertEqual(disp.estado_mesa(mesa, ini, fin, r("confirmada"), []), "reservada")
        self.assertEqual(disp.estado_mesa(mesa, ini, fin, r("cancelada"), []), "disponible")
        self.assertEqual(disp.estado_mesa(mesa, ini, fin, [], [disp.Intervalo(1, ini, fin, tipo="mantenimiento")]), "bloqueada")
        mesa.mantenimiento = True
        self.assertEqual(disp.estado_mesa(mesa, ini, fin, [], []), "bloqueada")

    def test_franjas_cuentan_mesas_libres(self):
        mesas = [disp.MesaDatos(1, "A", "pool", None), disp.MesaDatos(2, "B", "pool", None), disp.MesaDatos(3, "C", "carambola", None)]
        dia = date(2026, 11, 25)
        ocupada = [disp.Intervalo(1, disp.instante(dia, 1200), disp.instante(dia, 1320), estado="confirmada")]
        franjas = {f["inicio_min"]: f for f in disp.franjas_disponibles(dia, 60, "pool", mesas, ocupada, [], REGLAS, AHORA)}
        self.assertEqual(franjas[1200]["libres"], 1)
        self.assertEqual(franjas[1200]["total"], 2)
        self.assertEqual(franjas[1320]["libres"], 2)

    def test_valor_estimado(self):
        self.assertEqual(disp.valor_estimado(12000, 90), 18000)
        self.assertIsNone(disp.valor_estimado(None, 60))


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("cargar_datos_iniciales", verbosity=0)
        self.fecha = disp.hoy_bogota() + timedelta(days=2)
        self.pool = Mesa.objects.filter(modalidad="pool", activa=True).first()
        self.cliente = Client()

    def datos_reserva(self, **extra):
        d = {"modalidad": "pool", "fecha": self.fecha.isoformat(), "inicio": 1200, "duracion": 120, "mesa_id": self.pool.id,
             "nombre": "Ana Pérez", "celular": "300 123 4567", "correo": "ana@ejemplo.test", "acepta_datos": True, "website": ""}
        d.update(extra)
        return d

    def post(self, url, datos):
        return self.cliente.post(url, json.dumps(datos), content_type="application/json")


class ProteccionDobleReserva(Base):
    def test_segunda_reserva_en_el_mismo_horario_falla(self):
        crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=120, mesa_id=self.pool.id,
                      nombre="A", celular="3000000001", correo="a@ejemplo.test")
        with self.assertRaises(ErrorNegocio) as ctx:
            crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1260, duracion=60, mesa_id=self.pool.id,
                          nombre="B", celular="3000000002", correo="b@ejemplo.test")
        self.assertEqual(ctx.exception.codigo, "conflicto")

    def test_reserva_contigua_si_se_permite(self):
        crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=120, mesa_id=self.pool.id,
                      nombre="A", celular="3000000001", correo="a@ejemplo.test")
        r = crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1320, duracion=60, mesa_id=self.pool.id,
                          nombre="B", celular="3000000002", correo="b@ejemplo.test")
        self.assertEqual(r.estado, Reserva.Estado.PENDIENTE)

    def test_cancelada_libera_la_mesa(self):
        r = crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=120, mesa_id=self.pool.id,
                          nombre="A", celular="3000000001", correo="a@ejemplo.test")
        r.estado = Reserva.Estado.CANCELADA
        r.save()
        crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=120, mesa_id=self.pool.id,
                      nombre="B", celular="3000000002", correo="b@ejemplo.test")

    def test_bloqueo_impide_reservar(self):
        Bloqueo.objects.create(mesa=self.pool, inicio=disp.instante(self.fecha, 1140), fin=disp.instante(self.fecha, 1260), tipo="evento")
        with self.assertRaises(ErrorNegocio):
            crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=60, mesa_id=self.pool.id,
                          nombre="A", celular="3000000001", correo="a@ejemplo.test")

    def test_mesa_de_otra_modalidad_se_rechaza(self):
        carambola = Mesa.objects.filter(modalidad="carambola").first()
        with self.assertRaises(ErrorNegocio):
            crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=60, mesa_id=carambola.id,
                          nombre="A", celular="3000000001", correo="a@ejemplo.test")

    def test_modo_automatico_confirma(self):
        aj = Ajustes.actual()
        aj.modo_reserva = Ajustes.Modo.AUTOMATICA
        aj.save()
        r = crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=60, mesa_id=self.pool.id,
                          nombre="A", celular="3000000001", correo="a@ejemplo.test")
        self.assertEqual(r.estado, Reserva.Estado.CONFIRMADA)


class Apis(Base):
    def test_flujo_completo_de_reserva(self):
        disp_r = self.cliente.get(f"/api/disponibilidad/?modalidad=pool&fecha={self.fecha}&duracion=120").json()
        self.assertTrue(disp_r["ok"])
        self.assertTrue(any(f["inicio_min"] == 1200 and f["libres"] > 0 for f in disp_r["data"]["franjas"]))

        r = self.post("/api/reservas/", self.datos_reserva())
        self.assertEqual(r.status_code, 201, r.content)
        codigo = r.json()["data"]["codigo"]
        self.assertTrue(codigo.startswith("BG-"))
        self.assertEqual(Reserva.objects.get(codigo=codigo).celular, "3001234567")

        dup = self.post("/api/reservas/", self.datos_reserva(nombre="Otra", celular="3109998877"))
        self.assertEqual(dup.status_code, 409)

        mesas = self.cliente.get(f"/api/disponibilidad/?modalidad=pool&fecha={self.fecha}&duracion=120&inicio=1200").json()
        estado = {m["id"]: m["estado"] for m in mesas["data"]["mesas"]}
        self.assertEqual(estado[self.pool.id], "pendiente")

        ok = self.post("/api/reservas/consultar/", {"codigo": codigo.lower(), "celular": "3001234567"})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["data"]["codigo"], codigo)
        mal = self.post("/api/reservas/consultar/", {"codigo": codigo, "celular": "3000000000"})
        self.assertFalse(mal.json()["ok"])

    def test_validaciones(self):
        r = self.post("/api/reservas/", self.datos_reserva(celular="12345", acepta_datos=False))
        self.assertEqual(r.status_code, 422)
        self.assertIn("celular", r.json()["campos"])
        self.assertIn("acepta_datos", r.json()["campos"])

    def test_campo_trampa_bloquea_bots(self):
        r = self.post("/api/reservas/", self.datos_reserva(website="http://spam"))
        self.assertNotEqual(r.status_code, 201)
        self.assertFalse(Reserva.objects.exists())

    def test_limite_de_envios(self):
        codigos = [self.post("/api/reservas/", self.datos_reserva(inicio=600 + i * 120)).status_code for i in range(7)]
        self.assertEqual(codigos[-1], 429)

    def test_csrf_obligatorio(self):
        estricto = Client(enforce_csrf_checks=True)
        r = estricto.post("/api/contacto/", json.dumps({}), content_type="application/json")
        self.assertEqual(r.status_code, 403)


class Paginas(Base):
    def test_paginas_publicas(self):
        for url in ["/", "/club/", "/reservas/", "/reservas/consultar/", "/escuela/", "/torneos/", "/eventos/",
                    "/galeria/", "/contacto/", "/privacidad/", "/creditos/", "/sitemap.xml", "/robots.txt"]:
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(url).status_code, 200)
        self.assertEqual(self.cliente.get("/no-existe/").status_code, 404)

    def test_panel_requiere_ingreso_y_carga(self):
        self.assertEqual(self.cliente.get("/admin/club/reserva/").status_code, 302)
        admin = get_user_model().objects.create_superuser("admin-prueba", "x@ejemplo.test", "clave-de-prueba-larga")
        self.cliente.force_login(admin)
        crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=60, mesa_id=self.pool.id,
                      nombre="A", celular="3000000001", correo="a@ejemplo.test")
        for url in ["/admin/", "/admin/club/reserva/", "/admin/club/mesa/", "/admin/club/torneo/", "/admin/club/clase/",
                    "/admin/club/solicitudevento/", "/admin/club/mensajecontacto/", "/admin/club/fotogaleria/",
                    "/admin/club/inscripcionclase/", "/admin/club/inscripciontorneo/", "/admin/club/ajustes/"]:
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(url).status_code, 200)

    def test_accion_confirmar_del_panel(self):
        admin = get_user_model().objects.create_superuser("admin-prueba", "x@ejemplo.test", "clave-de-prueba-larga")
        self.cliente.force_login(admin)
        r = crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=1200, duracion=60, mesa_id=self.pool.id,
                          nombre="A", celular="3000000001", correo="a@ejemplo.test")
        self.cliente.post("/admin/club/reserva/", {"action": "confirmar", "_selected_action": [r.pk]})
        r.refresh_from_db()
        self.assertEqual(r.estado, Reserva.Estado.CONFIRMADA)
        self.assertEqual(r.historial[-1]["accion"], "confirmada")


class RobustezApiTests(TestCase):
    """El API responde 4xx (nunca 500) ante cuerpos raros y no se deja saltar el límite de envíos."""

    def test_cuerpo_json_que_no_es_objeto_da_422(self):
        for cuerpo in ["[1, 2]", '"texto"', "123", "null", "{no es json"]:
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post("/api/reservas/consultar/", data=cuerpo, content_type="application/json")
                self.assertEqual(r.status_code, 422)

    def test_limite_de_envios_no_se_evade_con_ip_falsa(self):
        from django.core.cache import cache

        cache.clear()
        cuerpo = '{"codigo": "BG-AAAAAA", "celular": "3001234567"}'
        codigos = [
            self.client.post("/api/reservas/consultar/", data=cuerpo, content_type="application/json",
                             HTTP_X_FORWARDED_FOR=f"9.9.9.{i}, 203.0.113.7").status_code
            for i in range(20)
        ]
        self.assertIn(429, codigos)


class AjustesYSeguridadTests(TestCase):
    def test_intervalo_cero_no_cuelga_y_el_panel_lo_rechaza(self):
        from django.core.exceptions import ValidationError
        from .servicios import reglas_actuales

        aj = Ajustes.actual()
        aj.intervalo_min = 0
        with self.assertRaises(ValidationError):
            aj.full_clean()
        self.assertGreaterEqual(reglas_actuales(aj).intervalo_min, 5)

    def test_historial_del_panel_escapa_html(self):
        from .admin import ReservaAdmin
        from django.contrib import admin as dj_admin

        mesa = Mesa.objects.create(nombre="M", modalidad="pool")
        ini = disp.instante(date.today() + timedelta(days=3), 600)
        r = Reserva.objects.create(mesa=mesa, modalidad="pool", inicio=ini, fin=ini + timedelta(hours=1), nombre="A",
                                   celular="3000000001", correo="a@ejemplo.test",
                                   historial=[{"fecha": "2026-11-23T10:00:00", "accion": "editada", "detalle": "<script>alert(1)</script>"}])
        html = str(ReservaAdmin(Reserva, dj_admin.site).historial_legible(r))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_json_ld_no_puede_cerrar_el_script(self):
        from .context_processors import _json_ld

        self.assertNotIn("</", _json_ld())


# ====================================================================== Calidad, seguridad y regresiones
import re
from html.parser import HTMLParser

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, override_settings

from .middleware import PERMISSIONS_POLICY, construir_csp

PAGINAS = ["/", "/club/", "/reservas/", "/reservas/consultar/", "/escuela/", "/torneos/", "/eventos/", "/galeria/",
           "/contacto/", "/privacidad/", "/creditos/"]


class CabecerasSeguridad(Base):
    def test_cabeceras_en_paginas_y_404(self):
        for url in ["/", "/contacto/", "/no-existe/", "/robots.txt"]:
            with self.subTest(url=url):
                r = self.cliente.get(url)
                self.assertIn("default-src 'self'", r["Content-Security-Policy"])
                self.assertEqual(r["Permissions-Policy"], PERMISSIONS_POLICY)
                self.assertEqual(r["X-Content-Type-Options"], "nosniff")
                self.assertEqual(r["X-Frame-Options"], "DENY")
                self.assertEqual(r["Cross-Origin-Opener-Policy"], "same-origin")
                self.assertEqual(r["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_cabeceras_en_la_api_y_el_panel(self):
        self.assertIn("frame-ancestors 'none'", self.cliente.get("/api/disponibilidad/?modalidad=pool")["Content-Security-Policy"])
        self.assertIn("Content-Security-Policy", self.cliente.get("/admin/login/"))


class PoliticaCSP(SimpleTestCase):
    def test_politica_base_es_estricta(self):
        csp = construir_csp(ga_id="", google_fonts=False, upgrade=True)
        for esperado in ["default-src 'self'", "object-src 'none'", "base-uri 'self'", "form-action 'self'",
                         "frame-ancestors 'none'", "upgrade-insecure-requests", "frame-src https://www.google.com"]:
            self.assertIn(esperado, csp)
        self.assertNotIn("googletagmanager", csp)
        self.assertNotIn("fonts.googleapis.com", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertNotIn("*", csp.replace("https://*.", ""))  # sin comodines abiertos

    def test_ga_y_fuentes_solo_si_se_piden(self):
        csp = construir_csp(ga_id="G-ABC", google_fonts=True, upgrade=False)
        self.assertIn("https://www.googletagmanager.com", csp)
        self.assertIn("https://fonts.googleapis.com", csp)
        self.assertIn("https://fonts.gstatic.com", csp)
        self.assertNotIn("upgrade-insecure-requests", csp)

    def test_plantillas_no_cargan_origenes_fuera_de_la_politica(self):
        """Todo origen https externo cargado por las plantillas (src/href de recursos) debe estar permitido en la CSP."""
        import pathlib
        permitido = construir_csp(ga_id="G-X", google_fonts=True)
        patron = re.compile(r"<(?:script|iframe|img|video|source|link)\b[^>]*?(?:src|href)=\"(https://[^/\"]+)")
        for f in pathlib.Path(__file__).parent.glob("templates/**/*.html"):
            for m in patron.finditer(f.read_text(encoding="utf-8")):
                host = m.group(1)
                if "{{" in host or 'rel="canonical"' in m.group(0):
                    continue
                with self.subTest(archivo=f.name, host=host):
                    self.assertIn(host, permitido)


class Limites(Base):
    def test_limite_por_tipo_de_envio(self):
        codigos = [self.post("/api/contacto/", {"nombre": "A"}).status_code for _ in range(12)]
        self.assertIn(429, codigos)
        self.assertNotIn(500, codigos)

    def test_cuerpo_demasiado_grande_se_rechaza(self):
        with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=1000):
            r = self.client.post("/api/contacto/", data=json.dumps({"mensaje": "x" * 5000}), content_type="application/json")
        self.assertIn(r.status_code, (400, 413, 422))

    def test_limite_de_cuerpo_configurado(self):
        from django.conf import settings
        self.assertLessEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 2 * 1024 * 1024)


class Honeypot(Base):
    def test_honeypot_en_todos_los_formularios(self):
        for url in ["/api/contacto/", "/api/eventos/", "/api/clases/inscripcion/", "/api/torneos/inscripcion/", "/api/reservas/"]:
            with self.subTest(url=url):
                r = self.post(url, {"website": "http://spam.test", "nombre": "Bot", "celular": "3001234567"})
                self.assertNotIn(r.status_code, (200, 201, 500))


class Validaciones(Base):
    def test_no_hay_500_con_datos_basura(self):
        basura = {"modalidad": "x" * 500, "fecha": "no-fecha", "inicio": "abc", "duracion": -5, "mesa_id": "zzz",
                  "nombre": "<script>", "celular": None, "correo": "no-correo", "acepta_datos": "quizá"}
        for url in ["/api/reservas/", "/api/contacto/", "/api/eventos/", "/api/clases/inscripcion/", "/api/torneos/inscripcion/"]:
            with self.subTest(url=url):
                self.assertLess(self.post(url, basura).status_code, 500)
        for q in ["", "?modalidad=pool", "?modalidad=pool&fecha=2020-01-01&duracion=60", "?modalidad=zz&fecha=x&duracion=y"]:
            with self.subTest(q=q):
                self.assertLess(self.cliente.get("/api/disponibilidad/" + q).status_code, 500)

    def test_reserva_en_el_pasado_o_lejana_se_rechaza(self):
        for f in [disp.hoy_bogota() - timedelta(days=1), disp.hoy_bogota() + timedelta(days=400)]:
            r = self.post("/api/reservas/", self.datos_reserva(fecha=f.isoformat()))
            self.assertIn(r.status_code, (400, 409, 422))
        self.assertFalse(Reserva.objects.exists())

    def test_metodo_no_permitido(self):
        self.assertEqual(self.cliente.get("/api/reservas/").status_code, 405)


class Estaticos(Base):
    def test_fuentes_autoalojadas_existen_y_estan_referenciadas(self):
        css = finders.find("club/css/fuentes.css")
        self.assertTrue(css)
        texto = open(css, encoding="utf-8").read()
        rutas = re.findall(r"url\(([^)]+)\)", texto)
        self.assertGreaterEqual(len(rutas), 2)
        import os
        for ruta in rutas:
            self.assertTrue(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(css), ruta))), ruta)
        self.assertIn("font-display: swap", texto)

    def test_robots_y_sitemap(self):
        robots = self.cliente.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /admin/", robots)
        self.assertIn("Sitemap:", robots)
        sm = self.cliente.get("/sitemap.xml")
        self.assertEqual(sm.status_code, 200)
        self.assertIn("xml", sm["Content-Type"])
        urls = re.findall(r"<loc>https?://[^/]+(/[^<]*)</loc>", sm.content.decode())
        self.assertIn("/", urls)
        self.assertFalse([u for u in urls if u.startswith(("/admin", "/api"))])
        for u in urls:
            with self.subTest(url=u):
                self.assertEqual(self.cliente.get(u).status_code, 200)

    def test_imagenes_de_las_plantillas_existen(self):
        for url in PAGINAS:
            html = self.cliente.get(url).content.decode()
            for ruta in re.findall(r"(?:src|href|poster)=\"/static/([^\"?#]+)", html):
                with self.subTest(pagina=url, recurso=ruta):
                    self.assertTrue(finders.find(ruta), ruta)


class _Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if a.get("id"):
            self.ids.add(a["id"])


class EnlacesInternos(Base):
    def test_todo_enlace_interno_resuelve(self):
        vistos, rotos = set(), []
        for pagina in PAGINAS + ["/torneos/"]:
            p = _Enlaces()
            p.feed(self.cliente.get(pagina).content.decode())
            for href in p.hrefs:
                if not href.startswith("/") or href.startswith("//"):
                    continue
                destino = href.split("#")[0].split("?")[0]
                if not destino or destino in vistos or destino.startswith("/static/"):
                    continue
                vistos.add(destino)
                estado = self.cliente.get(destino).status_code
                if estado not in (200, 301, 302):
                    rotos.append((pagina, href, estado))
        self.assertEqual(rotos, [])
        self.assertGreater(len(vistos), 8)

    def test_anclas_internas_existen(self):
        for pagina in PAGINAS:
            p = _Enlaces()
            p.feed(self.cliente.get(pagina).content.decode())
            for href in p.hrefs:
                if href.startswith("#") and len(href) > 1:
                    with self.subTest(pagina=pagina, ancla=href):
                        self.assertIn(href[1:], p.ids)

    def test_enlaces_externos_seguros(self):
        """Los enlaces que abren pestaña nueva llevan rel=noopener."""
        for pagina in PAGINAS:
            html = self.cliente.get(pagina).content.decode()
            for etiqueta in re.findall(r"<a\b[^>]*href=\"https?://[^>]*target=\"_blank\"[^>]*>|<a\b[^>]*target=\"_blank\"[^>]*href=\"https?://[^>]*>", html):
                with self.subTest(pagina=pagina, etiqueta=etiqueta[:80]):
                    self.assertIn("noopener", etiqueta)


class ReservasLogicaConcurrente(Base):
    def test_dos_clientes_misma_franja_solo_uno_gana(self):
        otro = Client()
        a = self.post("/api/reservas/", self.datos_reserva())
        b = otro.post("/api/reservas/", json.dumps(self.datos_reserva(nombre="Otro", celular="3109998877")), content_type="application/json")
        self.assertEqual(sorted([a.status_code, b.status_code]), [201, 409])
        self.assertEqual(Reserva.objects.filter(mesa=self.pool).count(), 1)

    def test_franjas_solapadas_parciales_en_cadena(self):
        horas = [(1200, 120), (1230, 60), (1290, 60), (1140, 90), (1320, 60)]
        ok = []
        for i, (ini, dur) in enumerate(horas):
            try:
                crear_reserva(modalidad="pool", fecha=self.fecha, inicio_min=ini, duracion=dur, mesa_id=self.pool.id,
                              nombre=f"N{i}", celular=f"300000000{i}", correo=f"n{i}@ejemplo.test")
                ok.append((ini, dur))
            except ErrorNegocio:
                pass
        # No puede haber dos reservas activas que se solapen en la misma mesa.
        activas = list(Reserva.objects.filter(mesa=self.pool).exclude(estado=Reserva.Estado.CANCELADA).order_by("inicio"))
        for x, y in zip(activas, activas[1:]):
            self.assertLessEqual(x.fin, y.inicio)

    def test_consulta_de_reserva_ajena_no_filtra_datos(self):
        r = self.post("/api/reservas/", self.datos_reserva())
        codigo = r.json()["data"]["codigo"]
        malo = self.post("/api/reservas/consultar/", {"codigo": codigo, "celular": "3110000000"})
        self.assertNotIn("Ana", malo.content.decode())
        self.assertNotIn("ana@ejemplo.test", malo.content.decode())


class ProduccionConfig(SimpleTestCase):
    def test_settings_de_produccion_no_aceptan_debug_ni_clave_vacia(self):
        import subprocess, sys, os
        env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        env.update(DJANGO_DEBUG="0", DJANGO_SECRET_KEY="")
        r = subprocess.run([sys.executable, "-c", "import os;os.environ['DJANGO_SETTINGS_MODULE']='config.settings';"
                            "import django.conf;django.conf.settings.SECRET_KEY"], env=env, capture_output=True, text=True,
                           cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", r.stderr)


class Compresion(Base):
    def test_html_se_comprime_y_binarios_no(self):
        r = self.cliente.get("/", HTTP_ACCEPT_ENCODING="gzip")
        self.assertEqual(r.get("Content-Encoding"), "gzip")
        self.assertIn("Accept-Encoding", r["Vary"])
        sm = self.cliente.get("/sitemap.xml", HTTP_ACCEPT_ENCODING="gzip")
        self.assertEqual(sm.get("Content-Encoding"), "gzip")
        from django.http import HttpResponse
        from .middleware import CompresionTextoMiddleware
        peticion = type("R", (), {"META": {"HTTP_ACCEPT_ENCODING": "gzip"}})()
        img = HttpResponse(b"x" * 5000, content_type="image/webp")
        self.assertIsNone(CompresionTextoMiddleware(lambda r: img).process_response(peticion, img).get("Content-Encoding"))


class DatosConfirmadosTests(TestCase):
    """Los datos confirmados del club aparecen en el JSON-LD y en las páginas; no hay pendientes."""

    def test_json_ld_incluye_contacto_y_redes_confirmadas(self):
        import json
        import re

        html = self.client.get("/").content.decode()
        ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1))
        lugar = [n for n in ld["@graph"] if n["@type"] != "WebSite"][0]
        self.assertEqual(lugar["email"], "billaresguayabal1@gmail.com")
        self.assertEqual(lugar["telephone"], "+57 314 773 0533")
        self.assertEqual(lugar["address"]["streetAddress"], "Carrera 52 #9-17, Guayabal, Medellín")
        self.assertEqual(lugar["sameAs"], ["https://www.instagram.com/clubdebillaresguayabal/"])  # sin Facebook
        self.assertIn("openingHoursSpecification", lugar)

    def test_pie_y_contacto_muestran_correo_e_instagram_con_enlaces_seguros(self):
        html = self.client.get("/contacto/").content.decode()
        self.assertIn("mailto:billaresguayabal1@gmail.com", html)
        self.assertIn('href="https://www.instagram.com/clubdebillaresguayabal/" target="_blank" rel="noopener noreferrer"', html)
        self.assertNotIn("facebook.com", html)

    def test_no_quedan_datos_pendientes(self):
        from . import negocio

        self.assertEqual(negocio.datos_pendientes(), [])


@override_settings(RESERVAS_EN_LINEA=False)
class SoloWhatsAppTests(TestCase):
    """Con las reservas en línea apagadas (estado de producción), reservar es solo por WhatsApp."""

    def test_reserva_en_linea_apagada_en_toda_la_web(self):
        import re

        for ruta in ["/", "/club/", "/escuela/", "/torneos/", "/eventos/", "/galeria/", "/contacto/", "/reservas/"]:
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 200)
                html = r.content.decode()
                self.assertNotIn("/reservas/consultar/", html)
                self.assertNotIn("Consultar mi reserva", html)
                self.assertNotIn("Mi reserva", html)
                self.assertNotIn("reservas.js", html)
                for tag in re.findall(r'<a [^>]*data-evento="cta_reservar"[^>]*>', html):
                    self.assertIn('href="https://wa.me/', tag, tag)  # todo «Reservar» abre WhatsApp...
                    self.assertIn('rel="noopener noreferrer"', tag, tag)  # ...de forma segura

    def test_inicio_ofrece_whatsapp_y_no_reserva_en_linea(self):
        html = self.client.get("/").content.decode()
        self.assertIn("Reservar por WhatsApp", html)
        self.assertIn("Reservas por WhatsApp", html)
        self.assertNotIn("Reserva en línea", html)
        self.assertNotIn("Disponibilidad real", html)

    def test_pagina_de_reservas_muestra_mesas_y_tarifa_con_whatsapp(self):
        Mesa.objects.create(nombre="Mesa 1", modalidad="carambola", tarifa_hora=15000, orden=1)
        Mesa.objects.create(nombre="Mesa 2", modalidad="pool", tarifa_hora=15000, orden=2)
        html = self.client.get("/reservas/").content.decode()
        self.assertIn("$ 15.000", html)
        self.assertIn("Mesa 1", html)
        self.assertIn("https://wa.me/573147730533?text=", html)
        self.assertNotIn('id="form-reserva"', html)
        self.assertEqual(html.count('class="sala-ficha" data-mesa='), 2)  # una mesa seleccionable por mesa creada

    def test_cada_mesa_tiene_su_boton_reservar_con_su_nombre(self):
        """Sin JavaScript (noscript) cada mesa conserva su enlace de WhatsApp con su nombre en el mensaje."""
        import re
        from urllib.parse import unquote

        for i, mod in enumerate(["carambola"] * 5 + ["pool"] * 2, 1):
            Mesa.objects.create(nombre=f"Mesa {i}", modalidad=mod, tarifa_hora=15000, orden=i)
        html = self.client.get("/reservas/").content.decode()
        botones = re.findall(r'<a href="(https://wa\.me/[^"]+)"[^>]*aria-label="Reservar (Mesa \d) por WhatsApp"[^>]*>', html)
        self.assertEqual(len(botones), 7)
        for url, nombre in botones:
            self.assertIn(f"Mesa: {nombre}", unquote(url))  # el mensaje dice qué mesa se quiere

    def test_sala_interactiva_con_las_siete_mesas_y_sus_datos(self):
        import re

        for i, mod in enumerate(["carambola"] * 5 + ["pool"] * 2, 1):
            Mesa.objects.create(nombre=f"Mesa {i}", modalidad=mod, tarifa_hora=15000, orden=i)
        r = self.client.get("/reservas/")
        html = r.content.decode()
        sala = r.context["sala"]
        self.assertEqual([m["numero"] for m in sala["mesas"]], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual([m["modalidad"] for m in sala["mesas"]], ["carambola"] * 5 + ["pool"] * 2)
        self.assertTrue(all(m["tarifa"] == 15000 for m in sala["mesas"]))
        self.assertEqual(sala["telefono"], "573147730533")
        self.assertEqual((sala["aperturaMin"], sala["cierreMin"]), (9 * 60, 26 * 60))
        self.assertIn('id="sala-datos"', html)  # datos para la escena 3D
        self.assertIn("club/js/sala/principal.js", html)
        self.assertEqual(len(re.findall(r'class="sala-ficha" data-mesa="\d+"', html)), 7)
        for campo in ("sala-mesa", "sala-fecha", "sala-hora", "sala-duracion", "sala-jugadores", "sala-nombre"):
            self.assertIn(f'id="{campo}"', html)
        self.assertIn("sujeta a confirmación por WhatsApp", html)
        self.assertNotIn("mesa_grafica", html)
        self.assertNotIn('<svg viewBox="0 0 240 130"', html)  # ya no hay ilustraciones planas de mesas

    def test_promocion_en_la_calculadora_solo_si_esta_vigente_en_el_panel(self):
        from .models import Promocion

        Mesa.objects.create(nombre="Mesa 1", modalidad="carambola", tarifa_hora=15000, orden=1)
        Promocion.objects.all().delete()
        self.assertIsNone(self.client.get("/reservas/").context["sala"]["promo"])
        Promocion.objects.create(titulo="La hora de billar en cualquier mesa, a $ 8.000")
        self.assertEqual(self.client.get("/reservas/").context["sala"]["promo"], {"valorHora": 8000, "hastaMin": 900})
        Promocion.objects.update(activa=False)
        self.assertIsNone(self.client.get("/reservas/").context["sala"]["promo"])

    def test_archivos_de_la_sala_3d_existen(self):
        from django.contrib.staticfiles import finders

        for ruta in ("club/js/sala/principal.js", "club/js/sala/escena3d.js", "club/js/sala/plano.js",
                     "club/js/sala/formulario.js", "club/js/sala/precios.js", "club/js/sala/distribucion.js",
                     "club/js/sala/texturas.js", "club/js/sala/disponibilidad.js",
                     "club/vendor/three/three.module.min.js", "club/vendor/three/OrbitControls.js",
                     "club/vendor/three/RoundedBoxGeometry.js", "club/vendor/three/RoomEnvironment.js"):
            self.assertIsNotNone(finders.find(ruta), ruta)

    def test_consultar_redirige_a_reservas(self):
        r = self.client.get("/reservas/consultar/")
        self.assertRedirects(r, "/reservas/", fetch_redirect_response=False)

    def test_api_de_reservas_desactivada_no_crea_nada(self):
        mesa = Mesa.objects.create(nombre="M", modalidad="pool", tarifa_hora=15000)
        cuerpo = json.dumps({"modalidad": "pool", "fecha": "2030-01-02", "inicio": 600, "duracion": 60, "mesa_id": mesa.id,
                             "nombre": "Ana Pérez", "celular": "3001234567", "correo": "a@ejemplo.test", "acepta_datos": True})
        self.assertEqual(self.client.post("/api/reservas/", data=cuerpo, content_type="application/json").status_code, 410)
        self.assertEqual(self.client.post("/api/reservas/consultar/", data=cuerpo, content_type="application/json").status_code, 410)
        self.assertEqual(self.client.get("/api/disponibilidad/?modalidad=pool&fecha=2030-01-02&duracion=60").status_code, 410)
        self.assertEqual(Reserva.objects.count(), 0)
        # el resto de formularios (contacto, clases, torneos, eventos) sigue funcionando
        self.assertEqual(self.client.post("/api/contacto/", data="{}", content_type="application/json").status_code, 422)

    def test_json_ld_sin_reserveaction(self):
        import re

        def accion(html):
            return "ReserveAction" in re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1)

        self.assertFalse(accion(self.client.get("/").content.decode()))
        with override_settings(RESERVAS_EN_LINEA=True):
            self.assertTrue(accion(self.client.get("/").content.decode()))

    def test_con_el_interruptor_encendido_todo_sigue_igual(self):
        with override_settings(RESERVAS_EN_LINEA=True):
            html = self.client.get("/").content.decode()
            self.assertIn('href="/reservas/"', html)
            self.assertIn("/reservas/consultar/", html)
            self.assertEqual(self.client.get("/reservas/consultar/").status_code, 200)

    def test_boton_de_la_promocion_abre_whatsapp_de_carambola(self):
        import re

        from .models import Promocion

        Promocion.objects.all().delete()
        Promocion.objects.create(titulo="Promo", enlace_url="/reservas/?modalidad=carambola", enlace_texto="Reservar mesa de carambola")
        Promocion.objects.create(titulo="Otra", enlace_url="/eventos/", enlace_texto="Ver eventos")
        html = self.client.get("/").content.decode()
        botones = re.findall(r'<a [^>]*data-evento="promocion"[^>]*>', html)
        self.assertEqual(len(botones), 2)
        self.assertTrue(botones[0].startswith('<a href="https://wa.me/'))
        self.assertIn('rel="noopener noreferrer"', botones[0])
        self.assertIn('href="/eventos/"', botones[1])  # los enlaces que no son de reserva no cambian


class PaginaClubTests(TestCase):
    """La página «El club» muestra las mesas Jimar Europa y, cuando hay datos, el equipo."""

    def test_mesas_jimar_europa_con_su_ficha(self):
        for i, mod in enumerate(["carambola"] * 5 + ["pool"] * 2, 1):
            Mesa.objects.create(nombre=f"Mesa {i}", modalidad=mod, tarifa_hora=15000, orden=i)
        html = self.client.get("/club/").content.decode()
        self.assertIn("Jimar Europa", html)
        self.assertIn("Las 5 mesas de tres bandas", html)
        self.assertIn("2 mesas más", html)
        for dato in ("Pizarra de 50 mm", "Bandas KleMatch P37", "Nivelación de 27 puntos", "Estructura en acero"):
            self.assertIn(dato, html)
        self.assertIn('href="/reservas/#sala"', html)

    def test_equipo_oculto_sin_datos_y_visible_con_datos(self):
        from unittest import mock

        from . import negocio

        self.assertNotIn('id="equipo"', self.client.get("/club/").content.decode())
        equipo = [negocio.Integrante("Ana Pérez", "Administradora", "Atiende reservas y torneos.")]
        with mock.patch.object(negocio, "EQUIPO", equipo):
            html = self.client.get("/club/").content.decode()
        self.assertIn('id="equipo"', html)
        self.assertIn("Ana Pérez", html)
        self.assertIn("Administradora", html)
        self.assertIn(">AP<", html)  # sin foto se muestran las iniciales
