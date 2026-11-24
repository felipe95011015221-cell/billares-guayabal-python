"""Pruebas del desarrollo full stack: promociones, imágenes, acciones masivas, CSV, API de reservas."""
import io
import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import disponibilidad as disp
from .admin import motivo_no_reactivable
from .models import (Ajustes, Clase, FotoGaleria, InscripcionClase, InscripcionTorneo, MensajeContacto, Mesa,
                     Promocion, Reserva, SesionClase, Torneo, validar_tamano_imagen)


class PromocionesTests(TestCase):
    def test_vigencia_texto(self):
        self.assertEqual(Promocion().vigencia_texto, "")
        self.assertEqual(Promocion(vigencia_desde=date(2026, 12, 1), vigencia_hasta=date(2026, 12, 24)).vigencia_texto,
                         "Del 1 de diciembre al 24 de diciembre de 2026")
        self.assertEqual(Promocion(vigencia_hasta=date(2026, 12, 24)).vigencia_texto, "Hasta el 24 de diciembre de 2026")
        self.assertEqual(Promocion(vigencia_desde=date(2026, 12, 1)).vigencia_texto, "Desde el 1 de diciembre de 2026")
        self.assertEqual(Promocion(vigencia_desde=date(2026, 12, 1), vigencia_hasta=date(2026, 12, 1)).vigencia_texto, "Solo el 1 de diciembre de 2026")

    def test_clean_valida_fechas_y_enlace(self):
        with self.assertRaises(ValidationError):
            Promocion(titulo="x", vigencia_desde=date(2026, 5, 2), vigencia_hasta=date(2026, 5, 1)).clean()
        with self.assertRaises(ValidationError):
            Promocion(titulo="x", enlace_url="javascript:alert(1)").clean()
        Promocion(titulo="x", enlace_url="/reservas/").clean()

    def test_inicio_y_reservas_solo_vigentes_max_3(self):
        hoy = disp.hoy_bogota()
        for i in range(1, 6):
            Promocion.objects.create(titulo=f"P{i}", orden=i)
        Promocion.objects.create(titulo="Inactiva", activa=False)
        Promocion.objects.create(titulo="Vencida", vigencia_hasta=hoy - timedelta(days=1))
        Promocion.objects.create(titulo="Futura", vigencia_desde=hoy + timedelta(days=1))
        Promocion.objects.create(titulo="Hoy", vigencia_desde=hoy, vigencia_hasta=hoy, orden=0)
        for url in ("/", "/reservas/"):
            promos = self.client.get(url).context["promociones"]
            self.assertEqual([p.titulo for p in promos], ["Hoy", "P1", "P2"])

    def test_lista_vacia_sin_promociones(self):
        self.assertEqual(self.client.get("/").context["promociones"], [])
        self.assertEqual(self.client.get("/reservas/").context["promociones"], [])

    def test_datos_iniciales_sin_demo_no_crean_promociones(self):
        call_command("cargar_datos_iniciales", verbosity=0)
        self.assertEqual(Promocion.objects.count(), 0)

    def test_demo_marca_promocion_como_ejemplo(self):
        call_command("cargar_datos_iniciales", "--demo", verbosity=0)
        p = Promocion.objects.get()
        self.assertTrue(p.ejemplo)
        self.assertIn("Ejemplo", p.titulo)


class ImagenTests(TestCase):
    def test_rechaza_archivo_que_no_es_imagen(self):
        campo = FotoGaleria._meta.get_field("imagen").formfield()  # el mismo campo que usa el panel
        with self.assertRaises(ValidationError):
            campo.clean(SimpleUploadedFile("a.jpg", b"no soy una imagen", content_type="image/jpeg"))

    def test_rechaza_extension_no_permitida(self):
        f = FotoGaleria(alt="x", imagen=SimpleUploadedFile("a.svg", b"<svg/>", content_type="image/svg+xml"))
        with self.assertRaises(ValidationError):
            f.full_clean()

    def test_tamano_maximo(self):
        class Grande:
            size = 6 * 1024 * 1024
        with self.assertRaises(ValidationError):
            validar_tamano_imagen(Grande())

        class Normal:
            size = 1024
        validar_tamano_imagen(Normal())

    def test_acepta_png_valido(self):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (4, 4)).save(buf, "PNG")
        campo = FotoGaleria._meta.get_field("imagen").formfield()
        campo.clean(SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png"))

    def test_media_en_produccion_solo_con_serve_media(self):
        from django.urls import resolve, Resolver404
        # Con DEBUG=0 y sin SERVE_MEDIA la ruta no existe (tests corren con DEBUG=0).
        with self.assertRaises(Resolver404):
            resolve("/media/galeria/x.jpg")


def _admin_client():
    u = get_user_model().objects.create_superuser("adm", "a@example.com", "x")
    c = Client()
    c.force_login(u)
    return c


class InscripcionesAdminTests(TestCase):
    def setUp(self):
        self.c = _admin_client()
        clase = Clase.objects.create(titulo="Clase")
        self.sesion = SesionClase.objects.create(clase=clase, inicio=timezone.now() + timedelta(days=3), cupos=1)
        self.torneo = Torneo.objects.create(nombre="T", fecha=timezone.now() + timedelta(days=9), cupos=2, estado="inscripciones_abiertas", publicado=True)

    def _accion(self, nombre_url, accion, objs):
        return self.c.post(f"/admin/club/{nombre_url}/", {"action": accion, "_selected_action": [o.pk for o in objs]}, follow=True)

    def test_reactivar_no_supera_cupo_clase(self):
        activa = InscripcionClase.objects.create(sesion=self.sesion, nombre="Ana Uno", celular="3001111111", correo="a@a.co", estado="confirmada")
        cancelada = InscripcionClase.objects.create(sesion=self.sesion, nombre="Beto Dos", celular="3002222222", correo="b@a.co", estado="cancelada")
        r = self._accion("inscripcionclase", "confirmar", [cancelada])
        cancelada.refresh_from_db()
        self.assertEqual(cancelada.estado, "cancelada")
        self.assertContains(r, "no quedan cupos")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(motivo_no_reactivable(cancelada))
        activa.refresh_from_db()
        self.assertEqual(activa.estado, "confirmada")

    def test_reactivar_no_repite_celular_torneo(self):
        InscripcionTorneo.objects.create(torneo=self.torneo, nombre="Ana Uno", celular="3001111111", correo="a@a.co", estado="pendiente")
        dup = InscripcionTorneo.objects.create(torneo=self.torneo, nombre="Ana Otra", celular="3001111111", correo="a@a.co", estado="cancelada")
        r = self._accion("inscripciontorneo", "confirmar", [dup])
        dup.refresh_from_db()
        self.assertEqual(dup.estado, "cancelada")
        self.assertContains(r, "ya tiene otra inscripción activa")

    def test_confirmar_pendiente_y_reactivar_con_cupo(self):
        p = InscripcionTorneo.objects.create(torneo=self.torneo, nombre="Ana Uno", celular="3001111111", correo="a@a.co")
        c = InscripcionTorneo.objects.create(torneo=self.torneo, nombre="Beto Dos", celular="3002222222", correo="b@a.co", estado="cancelada")
        r = self._accion("inscripciontorneo", "confirmar", [p, c])
        p.refresh_from_db(); c.refresh_from_db()
        self.assertEqual((p.estado, c.estado), ("confirmada", "confirmada"))
        self.assertContains(r, "2 inscripción(es) confirmada(s)")

    def test_formulario_de_edicion_no_da_500(self):
        InscripcionClase.objects.create(sesion=self.sesion, nombre="Ana Uno", celular="3001111111", correo="a@a.co", estado="confirmada")
        otra = InscripcionClase.objects.create(sesion=self.sesion, nombre="Beto Dos", celular="3002222222", correo="b@a.co", estado="cancelada")
        r = self.c.post(f"/admin/club/inscripcionclase/{otra.pk}/change/", {
            "sesion": self.sesion.pk, "nombre": "Beto Dos", "celular": "3002222222", "correo": "b@a.co",
            "nivel_declarado": "", "estado": "confirmada",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No se puede dejar la inscripción activa")
        otra.refresh_from_db()
        self.assertEqual(otra.estado, "cancelada")


class PanelTests(TestCase):
    def setUp(self):
        self.c = _admin_client()
        self.mesa = Mesa.objects.create(nombre="Mesa 1", modalidad="pool")

    def _reserva(self, nombre="=Cliente"):
        ini = timezone.now() + timedelta(days=2)
        return Reserva.objects.create(mesa=self.mesa, modalidad="pool", inicio=ini, fin=ini + timedelta(hours=1),
                                      nombre=nombre, celular="3001234567", correo="c@c.co")

    def test_exportar_reservas_csv(self):
        r1 = self._reserva()
        resp = self.c.post("/admin/club/reserva/", {"action": "exportar_csv", "_selected_action": [r1.pk]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        texto = resp.content.decode("utf-8-sig")
        self.assertIn(r1.codigo, texto)
        self.assertIn("'=Cliente", texto)  # protegido contra inyección de fórmulas

    def test_exportar_mensajes_csv_y_marcar_no_leidos(self):
        m = MensajeContacto.objects.create(nombre="Luis Perez", correo="l@l.co", asunto="otro", mensaje="Hola, quiero info", leido=True)
        resp = self.c.post("/admin/club/mensajecontacto/", {"action": "exportar_csv", "_selected_action": [m.pk]})
        self.assertIn("Luis Perez", resp.content.decode("utf-8-sig"))
        self.c.post("/admin/club/mensajecontacto/", {"action": "marcar_no_leidos", "_selected_action": [m.pk]})
        m.refresh_from_db()
        self.assertFalse(m.leido)

    def test_paginas_del_panel_cargan(self):
        self._reserva()
        Promocion.objects.create(titulo="P")
        for ruta in ("reserva", "promocion", "mensajecontacto", "inscripcionclase", "inscripciontorneo"):
            self.assertEqual(self.c.get(f"/admin/club/{ruta}/").status_code, 200, ruta)
        self.assertEqual(self.c.get("/admin/club/reserva/?origen=web&q=Cliente").status_code, 200)
        self.assertEqual(self.c.get("/admin/club/reserva/add/").status_code, 200)

    def test_origen_por_defecto_en_alta_manual(self):
        r = self.c.get("/admin/club/reserva/add/")
        self.assertContains(r, 'value="panel" selected')


class ApiReservaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.mesa = Mesa.objects.create(nombre="Mesa <b>7</b>", modalidad="carambola", tarifa_hora=20000)

    def _cuerpo(self):
        hoy = disp.hoy_bogota()
        return {"modalidad": "carambola", "fecha": (hoy + timedelta(days=3)).isoformat(), "inicio": 1200, "duracion": 120,
                "mesa_id": self.mesa.id, "nombre": "Carlos Pérez", "celular": "300 123 4567", "correo": "c@c.co", "acepta_datos": True}

    def test_respuesta_incluye_resumen_y_whatsapp(self):
        r = self.client.post("/api/reservas/", json.dumps(self._cuerpo()), content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()["data"]
        for k in ("codigo", "estado_texto", "inicio", "fin", "mesa", "valor_estimado", "duracion_min", "nombre", "whatsapp_url", "mensaje_whatsapp"):
            self.assertIn(k, d)
        self.assertEqual(d["duracion_min"], 120)
        self.assertEqual(d["valor_estimado"], 40000)
        self.assertEqual(d["nombre"], "Carlos")
        self.assertTrue(d["whatsapp_url"].startswith("https://wa.me/"))
        self.assertIn(d["codigo"], d["mensaje_whatsapp"])
        self.assertIn(d["codigo"], d["whatsapp_url"])
        self.assertEqual(Reserva.objects.get().origen, "web")

    def test_errores_en_espanol(self):
        r = self.client.get("/api/disponibilidad/?modalidad=zzz&fecha=hoy&duracion=abc")
        self.assertEqual(r.status_code, 422)
        j = r.json()
        self.assertIn("modalidad", j["campos"])
        self.assertEqual(j["campos"]["modalidad"], "Elige carambola o pool.")
        self.assertIn("fecha", j["campos"])
        c = self._cuerpo(); c["duracion"] = 45
        r = self.client.post("/api/reservas/", json.dumps(c), content_type="application/json")
        self.assertIn("Duración no permitida", r.json()["error"])

    def test_ajustes_inconsistentes_rechazados(self):
        aj = Ajustes.actual()
        aj.intervalo_min = 0
        with self.assertRaises(ValidationError):
            aj.clean()


class JsReservasTests(TestCase):
    def test_js_escapa_y_dispara_evento(self):
        from pathlib import Path
        js = (Path(__file__).parent / "static/club/js/reservas.js").read_text()
        self.assertIn("esc(m.nombre)", js)
        self.assertIn('window.evento("reserva_creada"', js)
        self.assertIn('typeof window.evento === "function"', js)
        self.assertNotIn("transition-all", js)
        self.assertNotIn("uppercase", js)
