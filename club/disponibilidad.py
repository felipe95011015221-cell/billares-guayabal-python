"""
Motor de disponibilidad (funciones puras, sin consultas a la base de datos).
Se usa para mostrar la disponibilidad y para RE-VERIFICAR al confirmar una reserva.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")
ACTIVOS = ("pendiente", "confirmada", "en_curso")


def instante(fecha: date, minutos: int) -> datetime:
    """Fecha local de Bogotá + minutos desde las 00:00 (puede pasar de 1440) → datetime con zona."""
    return datetime.combine(fecha, time(0), tzinfo=BOGOTA) + timedelta(minutes=minutos)


def hoy_bogota(ahora: datetime | None = None) -> date:
    return (ahora or datetime.now(tz=BOGOTA)).astimezone(BOGOTA).date()


def etiqueta_minutos(minutos: int) -> str:
    h24 = (minutos // 60) % 24
    m = minutos % 60
    sufijo = "a. m." if h24 < 12 else "p. m."
    h12 = 12 if h24 % 12 == 0 else h24 % 12
    return f"{h12}:{m:02d} {sufijo}"


def etiqueta_duracion(minutos: int) -> str:
    if minutos < 60:
        return f"{minutos} min"
    h, m = divmod(minutos, 60)
    return f"{h} h {m} min" if m else f"{h} {'hora' if h == 1 else 'horas'}"


def se_solapan(a_ini: datetime, a_fin: datetime, b_ini: datetime, b_fin: datetime) -> bool:
    """Intervalos semiabiertos [inicio, fin): 10–12 y 12–14 NO se solapan."""
    return a_ini < b_fin and b_ini < a_fin


@dataclass
class MesaDatos:
    id: int
    nombre: str
    modalidad: str
    tarifa_hora: int | None
    activa: bool = True
    mantenimiento: bool = False


@dataclass
class Intervalo:
    mesa_id: int
    inicio: datetime
    fin: datetime
    estado: str = ""  # reservas
    tipo: str = ""  # bloqueos


def estado_mesa(mesa: MesaDatos, ini: datetime, fin: datetime, reservas: list[Intervalo], bloqueos: list[Intervalo]) -> str:
    """Prioridad: bloqueada > ocupada > reservada > pendiente > disponible."""
    if not mesa.activa or mesa.mantenimiento:
        return "bloqueada"
    bloq = [b for b in bloqueos if b.mesa_id == mesa.id and se_solapan(ini, fin, b.inicio, b.fin)]
    if any(b.tipo != "ocupada" for b in bloq):
        return "bloqueada"
    if bloq:
        return "ocupada"
    res = [r for r in reservas if r.mesa_id == mesa.id and r.estado in ACTIVOS and se_solapan(ini, fin, r.inicio, r.fin)]
    if any(r.estado == "en_curso" for r in res):
        return "ocupada"
    if any(r.estado == "confirmada" for r in res):
        return "reservada"
    if res:
        return "pendiente"
    return "disponible"


@dataclass
class Reglas:
    duraciones: list[int]
    intervalo_min: int
    anticipacion_min: int
    dias_max: int
    hora_apertura: int
    hora_cierre: int


def validar_horario(fecha: date, inicio_min: int, duracion: int, reglas: Reglas, ahora: datetime | None = None) -> str | None:
    """Devuelve un mensaje de error o None si el horario es válido."""
    ahora = ahora or datetime.now(tz=BOGOTA)
    if duracion not in reglas.duraciones:
        return "Duración no permitida."
    if inicio_min % reglas.intervalo_min:
        return "Hora de inicio no válida."
    if inicio_min < reglas.hora_apertura or inicio_min + duracion > reglas.hora_cierre:
        return "El horario está fuera del horario de atención."
    ini = instante(fecha, inicio_min)
    if ini < ahora + timedelta(minutes=reglas.anticipacion_min):
        return f"Las reservas requieren al menos {reglas.anticipacion_min} minutos de anticipación."
    if ini > ahora + timedelta(days=reglas.dias_max):
        return f"Solo se reciben reservas con hasta {reglas.dias_max} días de anticipación."
    return None


def franjas_disponibles(fecha: date, duracion: int, modalidad: str, mesas: list[MesaDatos], reservas: list[Intervalo],
                        bloqueos: list[Intervalo], reglas: Reglas, ahora: datetime | None = None) -> list[dict]:
    del_tipo = [m for m in mesas if m.modalidad == modalidad]
    franjas = []
    t = reglas.hora_apertura
    while t + duracion <= reglas.hora_cierre:
        if validar_horario(fecha, t, duracion, reglas, ahora) is None:
            ini, fin = instante(fecha, t), instante(fecha, t + duracion)
            libres = sum(1 for m in del_tipo if estado_mesa(m, ini, fin, reservas, bloqueos) == "disponible")
            franjas.append({"inicio_min": t, "etiqueta": etiqueta_minutos(t), "libres": libres, "total": len(del_tipo)})
        t += reglas.intervalo_min
    return franjas


def valor_estimado(tarifa_hora: int | None, duracion: int) -> int | None:
    return None if tarifa_hora is None else round(tarifa_hora * duracion / 60)
