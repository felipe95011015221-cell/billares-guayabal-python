"""
Carga los datos iniciales del club (idempotente: no duplica si ya existen).

  python manage.py cargar_datos_iniciales            # producción: mesas de ejemplo, clases propuestas, galería
  python manage.py cargar_datos_iniciales --demo     # además, reservas y un torneo FICTICIOS para probar (solo desarrollo)
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from club import negocio
from club.disponibilidad import hoy_bogota, instante
from club.models import Ajustes, Bloqueo, Clase, FotoGaleria, InscripcionTorneo, Mesa, Partido, Reserva, SesionClase, Torneo

MESAS_EJEMPLO = [("Mesa 1", "carambola"), ("Mesa 2", "carambola"), ("Mesa 3", "carambola"), ("Mesa 4", "carambola"),
                 ("Mesa 5", "pool"), ("Mesa 6", "pool")]

CLASES_PROPUESTAS = [
    ("Iniciación al billar", "ambas", "Iniciación", 90, "Postura, puente, agarre del taco y primeros golpes. Para quien nunca ha jugado o quiere empezar con buenas bases."),
    ("Carambola a tres bandas", "carambola", "Intermedio", 90, "Sistemas de diamantes, lectura de bandas y elección de la bola correcta para construir la carambola."),
    ("Pool para principiantes", "pool", "Básico", 60, "Reglas de bola 8 y bola 9, saque, control de la blanca y cómo planear las siguientes bolas."),
    ("Técnica y precisión", "ambas", "Intermedio", 90, "Efectos, fuerza, seguimiento y retroceso. Ejercicios de repetición para un golpe más limpio y constante."),
    ("Entrenamiento avanzado", "carambola", "Avanzado", 120, "Sesiones de alto volumen, posiciones de torneo y análisis de partidas para jugadores con experiencia competitiva."),
    ("Clases particulares", "ambas", "Todos los niveles", 60, "Una hora uno a uno, enfocada en lo que tú quieras mejorar. Horario a convenir."),
]


class Command(BaseCommand):
    help = "Carga mesas de ejemplo, clases propuestas y la galería inicial."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Agrega datos ficticios para probar (no usar en producción).")

    def handle(self, *args, demo=False, **opts):
        Ajustes.actual()
        if not Mesa.objects.exists():
            for i, (nombre, modalidad) in enumerate(MESAS_EJEMPLO, 1):
                Mesa.objects.create(nombre=nombre, modalidad=modalidad, orden=i)
            self.stdout.write("· 6 mesas de ejemplo (inventario por confirmar)")
        if not Clase.objects.exists():
            for i, (titulo, modalidad, nivel, dur, desc) in enumerate(CLASES_PROPUESTAS):
                Clase.objects.create(titulo=titulo, modalidad=modalidad, nivel=nivel, duracion_min=dur, descripcion=desc, orden=i)
            self.stdout.write("· 6 programas de clases PROPUESTOS (confirmada = no)")
        if not FotoGaleria.objects.exists():
            for i, f in enumerate(negocio.GALERIA_INICIAL):
                FotoGaleria.objects.create(ruta_estatica=f.archivo, alt=f.alt, categoria=f.categoria, ancho=f.ancho, alto=f.alto, orden=i)
            self.stdout.write(f"· {len(negocio.GALERIA_INICIAL)} fotos reales en la galería")
        if demo:
            self._demo()
        self.stdout.write(self.style.SUCCESS("Datos iniciales listos."))

    def _demo(self):
        if Reserva.objects.exists():
            self.stdout.write("· Datos demo ya existían; no se duplican.")
            return
        hoy = hoy_bogota()
        mesas = list(Mesa.objects.all())
        manana = hoy + timedelta(days=1)
        Bloqueo.objects.create(mesa=mesas[3], inicio=instante(manana, 9 * 60), fin=instante(manana, 14 * 60), tipo="mantenimiento", motivo="Cambio de paño (demo)")
        for mesa, dias, h, dur, estado, nombre in [
            (mesas[0], 1, 19, 120, "confirmada", "Cliente Demo 1"), (mesas[1], 1, 20, 90, "pendiente", "Cliente Demo 2"),
            (mesas[4], 1, 21, 60, "confirmada", "Cliente Demo 3"), (mesas[5], 2, 18, 120, "pendiente", "Cliente Demo 4"),
        ]:
            f = hoy + timedelta(days=dias)
            Reserva.objects.create(mesa=mesa, modalidad=mesa.modalidad, inicio=instante(f, h * 60), fin=instante(f, h * 60 + dur),
                                   nombre=nombre, celular="3000000000", correo="demo@example.com", estado=estado,
                                   observaciones="Reserva ficticia de demostración.",
                                   historial=[{"fecha": timezone.now().isoformat(), "accion": "creada (demo)"}])
        for i, c in enumerate(Clase.objects.all()):
            for semana in range(3):
                f = hoy + timedelta(days=2 + i + semana * 7)
                SesionClase.objects.create(clase=c, inicio=instante(f, (18 if i % 2 else 10) * 60), cupos=1 if "particulares" in c.slug else 6)
        t = Torneo.objects.create(nombre="Torneo de demostración · Tres bandas", modalidad="carambola",
                                  fecha=instante(hoy + timedelta(days=21), 14 * 60), formato="Eliminación directa a 20 carambolas",
                                  requisitos="Mayor de edad. Llegar 30 minutos antes.", cupos=16, estado=Torneo.Estado.ABIERTO, publicado=True,
                                  descripcion="Torneo FICTICIO para probar inscripciones y el cuadro de eliminación. No es un evento real.")
        jugadores = [f"Jugador {c}" for c in "ABCDEFGH"]
        for n in jugadores:
            InscripcionTorneo.objects.create(torneo=t, nombre=n, celular="3000000000"[:9] + str(jugadores.index(n)), correo="demo@example.com", estado="confirmada")
        for k in range(4):
            gano = k < 2
            Partido.objects.create(torneo=t, ronda=1, orden=k, jugador_a=jugadores[2 * k], jugador_b=jugadores[2 * k + 1],
                                   marcador_a=20 if gano else None, marcador_b=14 + k if gano else None, ganador="A" if gano else "")
        Partido.objects.create(torneo=t, ronda=2, orden=0, jugador_a=jugadores[0], jugador_b=jugadores[2])
        Partido.objects.create(torneo=t, ronda=2, orden=1)
        Partido.objects.create(torneo=t, ronda=3, orden=0)
        self.stdout.write(self.style.WARNING("· Datos FICTICIOS de demostración (reservas, horarios de clase y un torneo)"))
