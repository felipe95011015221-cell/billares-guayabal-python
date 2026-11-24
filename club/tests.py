"""Pruebas: reglas de disponibilidad, protección contra doble reserva, APIs, páginas y panel."""
import json
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

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
