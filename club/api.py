"""APIs JSON usadas por el asistente de reservas y los formularios del sitio."""
import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import forms, servicios
from .models import MensajeContacto, Reserva, SolicitudEvento

log = logging.getLogger(__name__)


def _ok(data, status=200):
    return JsonResponse({"ok": True, "data": data}, status=status)


def _error(mensaje, status=400, campos=None):
    return JsonResponse({"ok": False, "error": mensaje, "campos": campos or {}}, status=status)


def _errores(form):
    return {k: v[0] for k, v in form.errors.items()}


def _ip(request) -> str:
    return (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "local"))


def _limitar(request, nombre: str, maximo: int, ventana_s: int = 600) -> bool:
    """Límite simple de envíos por IP (caché en memoria; orientativo con varias instancias)."""
    clave = f"lim:{nombre}:{_ip(request)}"
    n = cache.get(clave, 0) + 1
    cache.set(clave, n, ventana_s)
    return n <= maximo


def _cuerpo(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return {}


def _manejar(request, nombre, form_cls, accion, limite=8):
    if not _limitar(request, nombre, limite):
        return _error("Has enviado demasiadas solicitudes. Intenta de nuevo en unos minutos.", 429)
    form = form_cls(_cuerpo(request))
    if not form.is_valid():
        return _error("Revisa los campos marcados.", 422, _errores(form))
    try:
        return _ok(accion(form.cleaned_data), 201)
    except servicios.ErrorNegocio as e:
        return _error(e.mensaje, 409 if e.codigo in {"conflicto", "sin_cupos"} else 400)
    except Exception:  # noqa: BLE001
        log.exception("Error en %s", nombre)
        return _error("No pudimos procesar tu solicitud. Intenta de nuevo o escríbenos por WhatsApp.", 500)


@require_GET
def disponibilidad(request):
    form = forms.ConsultaDisponibilidadForm(request.GET)
    if not form.is_valid():
        return _error("Parámetros inválidos.", 422, _errores(form))
    d = form.cleaned_data
    try:
        return _ok(servicios.consultar_disponibilidad(d["modalidad"], d["fecha"], d["duracion"], d.get("inicio")))
    except servicios.ErrorNegocio as e:
        return _error(e.mensaje, 422)


def _resumen_reserva(r: Reserva) -> dict:
    return {
        "codigo": r.codigo, "estado": r.estado, "estado_texto": r.get_estado_display(),
        "inicio": r.inicio.isoformat(), "fin": r.fin.isoformat(), "mesa": r.mesa.nombre,
        "modalidad": r.modalidad, "valor_estimado": r.valor_estimado,
    }


@require_POST
def crear_reserva(request):
    def accion(d):
        r = servicios.crear_reserva(
            modalidad=d["modalidad"], fecha=d["fecha"], inicio_min=d["inicio"], duracion=d["duracion"],
            mesa_id=d["mesa_id"], nombre=d["nombre"], celular=d["celular"], correo=d["correo"],
        )
        return _resumen_reserva(r)

    return _manejar(request, "reserva", forms.ReservaForm, accion, limite=6)


@require_POST
def consultar_reserva(request):
    def accion(d):
        r = Reserva.objects.select_related("mesa").filter(codigo=d["codigo"]).first()
        if not r or forms.normalizar_celular(r.celular) != d["celular"]:
            raise servicios.ErrorNegocio("No encontramos una reserva con ese código y celular.", "no_encontrado")
        return {**_resumen_reserva(r), "nombre": r.nombre.split(" ")[0]}

    return _manejar(request, "consulta", forms.ConsultaReservaForm, accion, limite=15)


@require_POST
def inscripcion_clase(request):
    def accion(d):
        i = servicios.inscribir_clase(sesion_id=d["sesion_id"], nombre=d["nombre"], celular=d["celular"],
                                      correo=d["correo"], nivel=d.get("nivel_declarado", ""))
        return {"codigo": i.codigo, "estado": i.estado}

    return _manejar(request, "clase", forms.InscripcionClaseForm, accion)


@require_POST
def inscripcion_torneo(request):
    def accion(d):
        i = servicios.inscribir_torneo(torneo_id=d["torneo_id"], nombre=d["nombre"], celular=d["celular"],
                                       correo=d["correo"], documento=d.get("documento", ""))
        return {"codigo": i.codigo, "estado": i.estado}

    return _manejar(request, "torneo", forms.InscripcionTorneoForm, accion)


@require_POST
def solicitud_evento(request):
    def accion(d):
        s = SolicitudEvento.objects.create(
            tipo=d["tipo"], fecha=d["fecha"], participantes=d["participantes"], nombre=d["nombre"],
            celular=d["celular"], correo=d["correo"], empresa=d.get("empresa", ""), mensaje=d.get("mensaje", ""),
        )
        return {"codigo": s.codigo}

    return _manejar(request, "evento", forms.SolicitudEventoForm, accion, limite=5)


@require_POST
def contacto(request):
    def accion(d):
        MensajeContacto.objects.create(nombre=d["nombre"], correo=d["correo"], celular=d.get("celular", ""),
                                       asunto=d["asunto"], mensaje=d["mensaje"])
        return {"recibido": True}

    return _manejar(request, "contacto", forms.ContactoForm, accion, limite=5)


