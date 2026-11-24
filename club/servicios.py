"""
Operaciones de negocio con garantías de concurrencia.

- Reservas: se bloquea la fila de la mesa (SELECT ... FOR UPDATE en PostgreSQL; en SQLite la transacción
  IMMEDIATE toma el bloqueo de escritura) y se vuelve a verificar la disponibilidad dentro de la transacción.
  En PostgreSQL, además, una restricción de exclusión (migración 0002) hace imposible guardar dos reservas
  activas solapadas en la misma mesa.
- Inscripciones: se bloquea la sesión/torneo y se verifican cupos dentro de la transacción.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import disponibilidad as disp
from .models import Ajustes, Bloqueo, InscripcionClase, InscripcionTorneo, Mesa, Reserva, SesionClase, Torneo


class ErrorNegocio(Exception):
    def __init__(self, mensaje: str, codigo: str = "invalido"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


MENSAJE_CONFLICTO = "Otra persona acaba de tomar esta mesa en ese horario. Elige otra mesa u hora."


def reglas_actuales(aj: Ajustes | None = None) -> disp.Reglas:
    aj = aj or Ajustes.actual()
    return disp.Reglas(
        duraciones=list(aj.duraciones), intervalo_min=max(5, aj.intervalo_min),  # 0 colgaría el cálculo de franjas
         anticipacion_min=aj.anticipacion_min,
        dias_max=aj.dias_max, hora_apertura=aj.hora_apertura, hora_cierre=aj.hora_cierre,
    )


def _mesas_datos(mesas) -> list[disp.MesaDatos]:
    return [disp.MesaDatos(m.id, m.nombre, m.modalidad, m.tarifa_hora, m.activa, m.mantenimiento) for m in mesas]


def _intervalos(desde, hasta, mesa_id: int | None = None, excluir_reserva: int | None = None):
    rq = Reserva.objects.filter(inicio__lt=hasta, fin__gt=desde, estado__in=Reserva.ACTIVOS)
    bq = Bloqueo.objects.filter(inicio__lt=hasta, fin__gt=desde)
    if mesa_id:
        rq, bq = rq.filter(mesa_id=mesa_id), bq.filter(mesa_id=mesa_id)
    if excluir_reserva:
        rq = rq.exclude(pk=excluir_reserva)
    reservas = [disp.Intervalo(r.mesa_id, r.inicio, r.fin, estado=r.estado) for r in rq]
    bloqueos = [disp.Intervalo(b.mesa_id, b.inicio, b.fin, tipo=b.tipo) for b in bq]
    return reservas, bloqueos


def consultar_disponibilidad(modalidad: str, fecha: date, duracion: int, inicio_min: int | None = None) -> dict:
    aj = Ajustes.actual()
    reglas = reglas_actuales(aj)
    if duracion not in reglas.duraciones:
        raise ErrorNegocio("Duración no permitida: elige una de las opciones del asistente.")
    desde, hasta = disp.instante(fecha, 0), disp.instante(fecha + timedelta(days=2), 0)
    mesas = list(Mesa.objects.filter(activa=True))
    reservas, bloqueos = _intervalos(desde, hasta)
    datos = _mesas_datos(mesas)
    resultado = {
        "franjas": disp.franjas_disponibles(fecha, duracion, modalidad, datos, reservas, bloqueos, reglas),
        "mesas": None,
        "modo_reserva": aj.modo_reserva,
    }
    if inicio_min is not None:
        error = disp.validar_horario(fecha, inicio_min, duracion, reglas)
        if error:
            raise ErrorNegocio(error)
        ini, fin = disp.instante(fecha, inicio_min), disp.instante(fecha, inicio_min + duracion)
        resultado["mesas"] = [
            {
                "id": m.id, "nombre": m.nombre, "tarifa_hora": m.tarifa_hora,
                "valor_estimado": disp.valor_estimado(m.tarifa_hora, duracion),
                "estado": disp.estado_mesa(m, ini, fin, reservas, bloqueos),
            }
            for m in datos if m.modalidad == modalidad
        ]
    return resultado


def crear_reserva(*, modalidad: str, fecha: date, inicio_min: int, duracion: int, mesa_id: int,
                  nombre: str, celular: str, correo: str, origen: str = "web") -> Reserva:
    aj = Ajustes.actual()
    error = disp.validar_horario(fecha, inicio_min, duracion, reglas_actuales(aj))
    if error:
        raise ErrorNegocio(error)
    ini, fin = disp.instante(fecha, inicio_min), disp.instante(fecha, inicio_min + duracion)
    estado = Reserva.Estado.CONFIRMADA if aj.modo_reserva == Ajustes.Modo.AUTOMATICA else Reserva.Estado.PENDIENTE
    try:
        with transaction.atomic():
            mesa = Mesa.objects.select_for_update().filter(pk=mesa_id, modalidad=modalidad, activa=True).first()
            if not mesa:
                raise ErrorNegocio("La mesa seleccionada no está disponible.", "no_encontrado")
            reservas, bloqueos = _intervalos(ini, fin, mesa_id=mesa.id)
            datos = _mesas_datos([mesa])[0]
            if disp.estado_mesa(datos, ini, fin, reservas, bloqueos) != "disponible":
                raise ErrorNegocio(MENSAJE_CONFLICTO, "conflicto")
            accion = "confirmada automáticamente" if estado == Reserva.Estado.CONFIRMADA else "solicitud recibida"
            return Reserva.objects.create(
                mesa=mesa, modalidad=modalidad, inicio=ini, fin=fin, nombre=nombre, celular=celular, correo=correo,
                estado=estado, origen=origen, valor_estimado=disp.valor_estimado(mesa.tarifa_hora, duracion),
                historial=[{"fecha": timezone.now().isoformat(), "accion": accion}],
            )
    except IntegrityError as e:  # restricción de exclusión de PostgreSQL
        raise ErrorNegocio(MENSAJE_CONFLICTO, "conflicto") from e


def verificar_reprogramacion(reserva: Reserva, inicio, fin, mesa: Mesa) -> None:
    """Lanza ErrorNegocio si el nuevo horario se cruza con otra reserva activa o un bloqueo."""
    reservas, bloqueos = _intervalos(inicio, fin, mesa_id=mesa.id, excluir_reserva=reserva.pk)
    datos = disp.MesaDatos(mesa.id, mesa.nombre, mesa.modalidad, mesa.tarifa_hora)  # ignora mantenimiento al reprogramar
    if disp.estado_mesa(datos, inicio, fin, reservas, bloqueos) != "disponible":
        raise ErrorNegocio("El nuevo horario se cruza con otra reserva o bloqueo de esa mesa.", "conflicto")


def registrar_historial(reserva: Reserva, accion: str, detalle: str = "") -> None:
    reserva.historial = [*reserva.historial, {"fecha": timezone.now().isoformat(), "accion": accion, "detalle": detalle}]


def inscribir_clase(*, sesion_id: int, nombre: str, celular: str, correo: str, nivel: str = "") -> InscripcionClase:
    try:
        with transaction.atomic():
            sesion = SesionClase.objects.select_for_update().select_related("clase").filter(pk=sesion_id).first()
            if not sesion or not sesion.clase.activa:
                raise ErrorNegocio("El horario seleccionado no existe.", "no_encontrado")
            if sesion.inicio < timezone.now():
                raise ErrorNegocio("Este horario ya pasó.")
            activas = sesion.inscripciones.exclude(estado=InscripcionClase.Estado.CANCELADA)
            if activas.count() >= sesion.cupos:
                raise ErrorNegocio("No quedan cupos en este horario.", "sin_cupos")
            if activas.filter(celular=celular).exists():
                raise ErrorNegocio("Ya tienes una inscripción en este horario.", "conflicto")
            return InscripcionClase.objects.create(sesion=sesion, nombre=nombre, celular=celular, correo=correo, nivel_declarado=nivel)
    except IntegrityError as e:
        raise ErrorNegocio("Ya tienes una inscripción en este horario.", "conflicto") from e


def inscribir_torneo(*, torneo_id: int, nombre: str, celular: str, correo: str, documento: str = "") -> InscripcionTorneo:
    try:
        with transaction.atomic():
            torneo = Torneo.objects.select_for_update().filter(pk=torneo_id, publicado=True).first()
            if not torneo:
                raise ErrorNegocio("Torneo no encontrado.", "no_encontrado")
            if torneo.estado != Torneo.Estado.ABIERTO:
                raise ErrorNegocio("Las inscripciones de este torneo no están abiertas.")
            activas = torneo.inscripciones.exclude(estado="cancelada")
            if activas.count() >= torneo.cupos:
                raise ErrorNegocio("El torneo no tiene cupos disponibles.", "sin_cupos")
            if activas.filter(celular=celular).exists():
                raise ErrorNegocio("Este celular ya está inscrito en el torneo.", "conflicto")
            return InscripcionTorneo.objects.create(torneo=torneo, nombre=nombre, celular=celular, correo=correo, documento=documento)
    except IntegrityError as e:
        raise ErrorNegocio("Este celular ya está inscrito en el torneo.", "conflicto") from e


def generar_cuadro(torneo: Torneo) -> int:
    """Cuadro de eliminación directa con los inscritos confirmados (orden de inscripción)."""
    from .models import Partido

    jugadores = list(torneo.inscripciones.filter(estado="confirmada").values_list("nombre", flat=True))
    if len(jugadores) < 2:
        raise ErrorNegocio("Se necesitan al menos 2 inscritos confirmados.")
    tam = 2
    while tam < len(jugadores):
        tam *= 2
    rondas = tam.bit_length() - 1
    with transaction.atomic():
        torneo.partidos.all().delete()
        for k in range(tam // 2):
            a = jugadores[k * 2] if k * 2 < len(jugadores) else ""
            b = jugadores[k * 2 + 1] if k * 2 + 1 < len(jugadores) else ""
            Partido.objects.create(torneo=torneo, ronda=1, orden=k, jugador_a=a, jugador_b=b, ganador="A" if a and not b else "")
        for r in range(2, rondas + 1):
            for k in range(tam // 2**r):
                Partido.objects.create(torneo=torneo, ronda=r, orden=k)
        avanzar_ganadores(torneo)
    return tam // 2


def avanzar_ganadores(torneo: Torneo) -> None:
    partidos = list(torneo.partidos.all())
    por_ronda: dict[int, list] = {}
    for p in partidos:
        por_ronda.setdefault(p.ronda, []).append(p)
    if not por_ronda:
        return
    for r in sorted(por_ronda)[:-1]:
        siguientes = sorted(por_ronda[r + 1], key=lambda x: x.orden)
        for p in sorted(por_ronda[r], key=lambda x: x.orden):
            ganador = p.jugador_a if p.ganador == "A" else p.jugador_b if p.ganador == "B" else ""
            sig = siguientes[p.orden // 2]
            if p.orden % 2 == 0:
                sig.jugador_a = ganador
            else:
                sig.jugador_b = ganador
            sig.save(update_fields=["jugador_a", "jugador_b"])
