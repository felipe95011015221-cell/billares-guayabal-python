"""Vistas de las páginas públicas."""
import re
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone

from . import negocio
from .disponibilidad import etiqueta_duracion, hoy_bogota
from .models import Ajustes, Clase, FotoGaleria, Modalidad, Promocion, SolicitudEvento, Torneo

ESTADOS_TORNEO_VISIBLES = [Torneo.Estado.ABIERTO, Torneo.Estado.CERRADO, Torneo.Estado.EN_JUEGO]
TONO_ESTADO_TORNEO = {
    "inscripciones_abiertas": "ok", "inscripciones_cerradas": "alerta", "en_juego": "oro",
    "finalizado": "neutro", "cancelado": "error", "borrador": "neutro",
}


def _recortar(texto: str, maximo: int) -> str:
    """Recorta en palabra completa, sin pasar de `maximo` caracteres."""
    texto = " ".join(texto.split())
    if len(texto) <= maximo:
        return texto
    return texto[:maximo].rsplit(" ", 1)[0].rstrip(" ,.;:·-")


def _torneos_publicos():
    qs = (
        Torneo.objects.filter(publicado=True).exclude(estado=Torneo.Estado.BORRADOR)
        .annotate(n_inscritos=Count("inscripciones", filter=~Q(inscripciones__estado="cancelada")))
    )
    for t in qs:
        t.libres = max(0, t.cupos - t.n_inscritos)
        t.tono = TONO_ESTADO_TORNEO.get(t.estado, "neutro")
        yield t


def _clases_publicas():
    ahora = timezone.now()
    clases = list(Clase.objects.filter(activa=True).select_related("instructor").prefetch_related("sesiones__inscripciones"))
    for c in clases:
        sesiones = [s for s in c.sesiones.all() if s.inicio > ahora][:6]
        for s in sesiones:
            s.disponibles = s.cupos - sum(1 for i in s.inscripciones.all() if i.estado != "cancelada")
        c.proximas = sesiones
        c.cupos_libres = sum(max(0, s.disponibles) for s in sesiones)
        c.duracion_texto = etiqueta_duracion(c.duracion_min)
    return clases


def _promociones_vigentes():
    """Hasta 3 promociones activas y vigentes hoy; lista vacía si el club no ha publicado ninguna."""
    return list(Promocion.objects.vigentes()[:3])


def inicio(request):
    aj = Ajustes.actual()
    torneos = [t for t in _torneos_publicos() if t.estado in ESTADOS_TORNEO_VISIBLES][:2]
    return render(request, "club/inicio.html", {
        "ajustes": aj,
        "titulo_hero": aj.texto_hero or "El billar se vive en Guayabal",
        "subtitulo_hero": aj.subtitulo_hero or (
            "Carambola a tres bandas y pool en Guayabal, Medellín. Reserva tu mesa en línea en menos de dos minutos."
            if settings.RESERVAS_EN_LINEA else
            "Carambola a tres bandas y pool en Guayabal, Medellín. Reserva tu mesa por WhatsApp y te la confirmamos."),
        "clases": _clases_publicas()[:3],
        "promociones": _promociones_vigentes(),
        "torneos": torneos,
        "fotos_inicio": negocio.FOTOS_INICIO,
        "jugador": negocio.JUGADOR_ESTUDIO,
        "video": negocio.VIDEO_EVENTO,
        "seo_titulo_absoluto": "Billares en Medellín · Club de Billares Guayabal",
        "seo_descripcion": ("Club de billar en Guayabal, Medellín: carambola a tres bandas y pool. Reserva tu mesa en línea y conoce la escuela, torneos y eventos."
                            if settings.RESERVAS_EN_LINEA else
                            "Club de billar en Guayabal, Medellín: carambola a tres bandas y pool. Reserva tu mesa por WhatsApp y conoce la escuela, torneos y eventos."),
    })


def _mesas_proximamente():
    """Mesas anunciadas que todavía no se pueden reservar (se muestran como «Próximamente»)."""
    from .models import Mesa

    return list(Mesa.objects.filter(activa=True, nombre__in=negocio.MESAS_PROXIMAMENTE).order_by("orden", "id"))


def club(request):
    cantidades = {g["clave"]: g["cantidad"] for g in _mesas_por_modalidad()}
    return render(request, "club/club.html", {
        "pool_proximamente": sum(1 for m in _mesas_proximamente() if m.modalidad == "pool"),
        "mesa_tres_bandas": negocio.MESA_TRES_BANDAS,
        "mesas_carambola": cantidades.get("carambola", 0),
        "mesas_pool": cantidades.get("pool", 0),
        "equipo": negocio.EQUIPO,
        "seo_titulo_absoluto": "El club · Billar en Guayabal, Medellín",
        "seo_descripcion": "Conoce el Club de Billares Guayabal: mesas de carambola a tres bandas y pool, ambiente para jugar, aprender y competir en Medellín.",
    })


def _mesas_por_modalidad():
    """Mesas activas por modalidad, con su tarifa por hora si es la misma para todas."""
    from .models import Mesa

    grupos = []
    for clave, nombre in Modalidad.choices:
        mesas = list(Mesa.objects.filter(activa=True, modalidad=clave).exclude(nombre__in=negocio.MESAS_PROXIMAMENTE)
                     .order_by("orden", "id"))
        for mesa in mesas:  # cada mesa tiene su botón «Reservar» con su nombre en el mensaje
            mesa.wa_url = negocio.enlace_whatsapp(f"reservas_{clave}", extra=f"Mesa: {mesa.nombre}")
        tarifas = {m.tarifa_hora for m in mesas}
        grupos.append({
            "clave": clave, "nombre": nombre, "mesas": mesas, "cantidad": len(mesas),
            "tarifa": tarifas.pop() if len(tarifas) == 1 else None,
            "wa_url": negocio.enlace_whatsapp(f"reservas_{clave}"),
        })
    return grupos


def _numero_mesa(mesa, respaldo: int) -> int:
    digitos = re.search(r"\d+", mesa.nombre or "")
    return int(digitos.group()) if digitos else respaldo


def _datos_sala(grupos):
    """Datos para la sala interactiva (JSON): mesas, horario, promoción y WhatsApp.

    No incluye ocupación: hoy no hay reservas en línea, así que la web no inventa estados.
    Cuando exista disponibilidad en tiempo real se agrega aquí (ver club/static/club/js/sala/disponibilidad.js).
    """
    mesas = []
    for g in grupos:
        for mesa in g["mesas"]:
            mesas.append({
                "id": mesa.id, "nombre": mesa.nombre, "numero": _numero_mesa(mesa, len(mesas) + 1),
                "modalidad": g["clave"], "modalidadNombre": g["nombre"],
                "tarifa": int(mesa.tarifa_hora) if mesa.tarifa_hora else None,
            })
    nombres_modalidad = dict(Modalidad.choices)
    proximamente = [{
        "id": f"proxima-{m.id}", "nombre": m.nombre, "numero": _numero_mesa(m, 0), "modalidad": m.modalidad,
        "modalidadNombre": nombres_modalidad.get(m.modalidad, m.modalidad), "tarifa": None,
    } for m in _mesas_proximamente()]
    valor_promo = f"{negocio.PROMO_HORA_VALOR:,}".replace(",", ".")
    hay_promo = Promocion.objects.vigentes().filter(titulo__contains=valor_promo).exists()
    ahora = timezone.localtime()
    return {
        "mesas": mesas,
        "proximamente": proximamente,  # se dibujan en la sala, pero no se pueden elegir
        "promo": {"valorHora": negocio.PROMO_HORA_VALOR, "hastaMin": negocio.PROMO_HORA_HASTA_MIN} if hay_promo else None,
        "aperturaMin": negocio.HORARIO_APERTURA_MIN, "cierreMin": negocio.HORARIO_CIERRE_MIN,
        "duraciones": list(negocio.SALA_DURACIONES), "diasMax": negocio.SALA_DIAS_MAX,
        "hoy": hoy_bogota().isoformat(), "ahoraMin": ahora.hour * 60 + ahora.minute,
        "telefono": negocio.TELEFONO_E164, "mensaje": negocio.SALA_MENSAJE,
    }


def _reservas_por_whatsapp(request):
    modalidades = _mesas_por_modalidad()
    return render(request, "club/reservas_whatsapp.html", {
        "modalidades": modalidades,
        "sala": _datos_sala(modalidades),
        "wa_reservas": negocio.enlace_whatsapp("reservas"),
        "promociones": list(Promocion.objects.vigentes()[:3]),
        "seo_titulo_absoluto": "Reservar mesa de billar en Medellín | Guayabal",
        "seo_descripcion": "Reserva tu mesa de carambola o pool en el Club de Billares Guayabal por WhatsApp. Mira las mesas, la tarifa por hora y las promociones.",
    })


@ensure_csrf_cookie
def reservas(request):
    if not settings.RESERVAS_EN_LINEA:
        return _reservas_por_whatsapp(request)
    aj = Ajustes.actual()
    hoy = hoy_bogota()
    modalidad = request.GET.get("modalidad")
    return render(request, "club/reservas.html", {
        "ajustes": aj,
        "promociones": _promociones_vigentes(),
        "config_reserva": {
            "modalidadInicial": modalidad if modalidad in Modalidad.values else None,
            "duraciones": [{"min": d, "texto": etiqueta_duracion(d)} for d in aj.duraciones],
            "hoy": hoy.isoformat(),
            "maximo": (hoy + timedelta(days=aj.dias_max)).isoformat(),
            "modoReserva": aj.modo_reserva,
            "whatsapp": negocio.enlace_whatsapp("reservas"),
            "telefono": negocio.TELEFONO_E164,
        },
        "seo_titulo_absoluto": "Reservar mesa de billar en Medellín | Guayabal",
        "seo_descripcion": "Reserva tu mesa de carambola o pool en el Club de Billares Guayabal. Mira la disponibilidad, escoge hora y recibe tu código.",
    })


@ensure_csrf_cookie
def consultar_reserva(request):
    if not settings.RESERVAS_EN_LINEA:
        return redirect("reservas")
    return render(request, "club/consultar.html", {
        "seo_titulo": "Consultar mi reserva", "seo_noindex": True,
        "seo_descripcion": "Consulta el estado de tu reserva en el Club de Billares Guayabal con tu código y celular.",
    })


@ensure_csrf_cookie
def escuela(request):
    clases = _clases_publicas()
    calendario = sorted(((s, c) for c in clases for s in c.proximas), key=lambda x: x[0].inicio)[:10]
    return render(request, "club/escuela.html", {
        "clases": clases, "calendario": calendario, "hay_propuestas": any(not c.confirmada for c in clases),
        "seo_titulo_absoluto": "Clases de billar en Medellín · Escuela Guayabal",
        "seo_descripcion": "Clases de billar en Medellín: carambola a tres bandas y pool, para principiantes y jugadores avanzados. Consulta horarios e inscripción por WhatsApp.",
    })


def torneos(request):
    todos = list(_torneos_publicos())
    return render(request, "club/torneos.html", {
        "activos": [t for t in todos if t.estado in ESTADOS_TORNEO_VISIBLES],
        "pasados": [t for t in todos if t.estado == Torneo.Estado.FINALIZADO],
        "seo_titulo_absoluto": "Torneos de billar en Medellín · Guayabal",
        "seo_descripcion": "Torneos de carambola a tres bandas y pool en el Club de Billares Guayabal: fechas, formato, cupos e inscripción en línea.",
    })


@ensure_csrf_cookie
def torneo_detalle(request, slug):
    t = next((x for x in _torneos_publicos() if x.slug == slug), None)
    if not t:
        raise Http404
    partidos = list(t.partidos.all())
    rondas = sorted({p.ronda for p in partidos})
    total = rondas[-1] if rondas else 0

    def nombre_ronda(r):
        return {0: "Final", 1: "Semifinal", 2: "Cuartos de final"}.get(total - r, f"Ronda {r}")

    return render(request, "club/torneo_detalle.html", {
        "t": t,
        "cuadro": [{"nombre": nombre_ronda(r), "partidos": [p for p in partidos if p.ronda == r]} for r in rondas],
        "confirmados": t.inscripciones.filter(estado="confirmada"),
        "abierto": t.estado == Torneo.Estado.ABIERTO and t.libres > 0,
        "seo_titulo_absoluto": _recortar(f"{t.nombre} · Torneo de billar en Medellín", 60),
        "seo_descripcion": _recortar(f"{t.formato}. {t.descripcion}", 155),
    })


@ensure_csrf_cookie
def eventos(request):
    return render(request, "club/eventos.html", {
        "tipos": SolicitudEvento.Tipo.choices,
        "manana": (hoy_bogota() + timedelta(days=1)).isoformat(),
        "video": negocio.VIDEO_EVENTO,
        "seo_titulo_absoluto": "Eventos con billar en Medellín · Empresas y fiestas",
        "seo_descripcion": "Eventos empresariales, cumpleaños y celebraciones con billar en Guayabal, Medellín. Cuéntanos tu plan y te respondemos con propuesta.",
    })


def galeria(request):
    fotos = list(FotoGaleria.objects.filter(visible=True))
    categorias = [(c, n, sum(1 for f in fotos if f.categoria == c)) for c, n in FotoGaleria.Categoria.choices]
    return render(request, "club/galeria.html", {
        "fotos": fotos, "categorias": [c for c in categorias if c[2] > 0],
        "seo_titulo_absoluto": "Galería · Club de Billares Guayabal, Medellín",
        "seo_descripcion": "Fotos del Club de Billares Guayabal en Medellín: el salón, las mesas de carambola, la barra y el ambiente de las noches de juego.",
    })


@ensure_csrf_cookie
def contacto(request):
    return render(request, "club/contacto.html", {
        "asuntos": [("reservas", "Reservas"), ("clases", "Clases"), ("torneos", "Torneos"), ("eventos", "Eventos")],
        "seo_titulo_absoluto": "Contacto y cómo llegar · Billares Guayabal",
        "seo_descripcion": "Escríbenos por WhatsApp o déjanos un mensaje. Ubicación, mapa y cómo llegar al Club de Billares Guayabal, en Medellín.",
    })


def privacidad(request):
    return render(request, "club/privacidad.html", {"seo_titulo_absoluto": "Tratamiento de datos personales · Billares Guayabal",
                                                     "seo_descripcion": "Política de tratamiento de datos personales del Club de Billares Guayabal."})


def creditos(request):
    return render(request, "club/creditos.html", {"fotos": negocio.FOTOS_REFERENCIA, "seo_titulo": "Créditos fotográficos",
                                                   "seo_noindex": True, "seo_descripcion": "Fuentes, autores y licencias de las fotografías de referencia."})


def robots(request):
    from django.conf import settings

    contenido = f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\nDisallow: /reservas/consultar/\n\nSitemap: {settings.SITE_URL}/sitemap.xml\n"
    return HttpResponse(contenido, content_type="text/plain")


def error_404(request, exception):
    return render(request, "club/404.html", status=404)
