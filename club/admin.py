"""Panel de administración del club (Django admin, en español)."""
import csv

from django import forms
from django.conf import settings
from django import forms
from django.contrib import admin, messages
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from . import negocio
from .models import (Ajustes, Bloqueo, Clase, FotoGaleria, InscripcionClase, InscripcionTorneo, Instructor,
                     MensajeContacto, Mesa, Partido, Promocion, Reserva, SesionClase, SolicitudEvento, Torneo)
from .servicios import ErrorNegocio, avanzar_ganadores, generar_cuadro, registrar_historial, verificar_reprogramacion
from .templatetags.club_tags import fecha_corta, hora

admin.site.site_header = "Club de Billares Guayabal · Administración"
admin.site.site_title = "Administración del club"
admin.site.index_title = "Panel del club"

COLORES = {"pendiente": "#d9a441", "confirmada": "#5fbf8a", "en_curso": "#c9a35c", "finalizada": "#8a8a8a",
           "cancelada": "#c4453a", "rechazada": "#c4453a", "nueva": "#d9a441", "en_revision": "#c9a35c",
           "aprobada": "#5fbf8a", "cerrada": "#8a8a8a"}


def insignia(valor, texto):
    color = COLORES.get(valor, "#8a8a8a")
    return format_html('<span style="padding:2px 8px;border-radius:999px;border:1px solid {0};color:{0};'
                       'font-size:11px;white-space:nowrap">{1}</span>', color, texto)


def enlace_whatsapp(celular, texto):
    if not celular:
        return "—"
    from urllib.parse import quote
    return format_html('<a href="https://wa.me/57{}?text={}" target="_blank" rel="noopener">{}</a>', celular, quote(texto), celular)


def _celda_csv(valor):
    """Evita inyección de fórmulas al abrir el CSV en Excel/Sheets."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def respuesta_csv(nombre_archivo, encabezados, filas):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{nombre_archivo}-{timezone.localdate():%Y%m%d}.csv"'
    resp.write("\ufeff")  # BOM para que Excel respete las tildes
    w = csv.writer(resp)
    w.writerow(encabezados)
    for fila in filas:
        w.writerow([_celda_csv(c) for c in fila])
    return resp


# ---------------------------------------------------------------- Configuración y mesas
@admin.register(Ajustes)
class AjustesAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Reservas", {"fields": ["modo_reserva", "duraciones", "intervalo_min", "anticipacion_min", "dias_max"]}),
        ("Horario de reservas en línea", {"fields": ["hora_apertura", "hora_cierre"],
                                          "description": "Minutos desde la medianoche. 540 = 9:00 a. m.; 1560 = 2:00 a. m. del día siguiente."}),
        ("Textos", {"fields": ["politica", "texto_hero", "subtitulo_hero"]}),
    ]

    def has_add_permission(self, request):
        return not Ajustes.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class BloqueoEnLinea(admin.TabularInline):
    model = Bloqueo
    extra = 0
    fields = ["inicio", "fin", "tipo", "motivo"]


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "modalidad", "tarifa", "activa", "mantenimiento", "orden"]
    list_editable = ["activa", "mantenimiento", "orden"]
    list_filter = ["modalidad", "activa", "mantenimiento"]
    inlines = [BloqueoEnLinea]

    @admin.display(description="Tarifa por hora")
    def tarifa(self, obj):
        return f"$ {obj.tarifa_hora:,}".replace(",", ".") if obj.tarifa_hora else "Por confirmar"


@admin.register(Bloqueo)
class BloqueoAdmin(admin.ModelAdmin):
    list_display = ["mesa", "inicio", "fin", "tipo", "motivo"]
    list_filter = ["tipo", "mesa"]
    date_hierarchy = "inicio"


# ---------------------------------------------------------------- Reservas
class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = "__all__"

    def clean(self):
        datos = super().clean()
        inicio, fin, mesa, estado = datos.get("inicio"), datos.get("fin"), datos.get("mesa"), datos.get("estado")
        if inicio and fin and mesa and estado in Reserva.ACTIVOS:
            if fin <= inicio:
                raise forms.ValidationError("La hora de fin debe ser posterior al inicio.")
            try:
                verificar_reprogramacion(self.instance, inicio, fin, mesa)
            except ErrorNegocio as e:
                raise forms.ValidationError(e.mensaje)
        return datos


def _cambiar_estado(modeladmin, request, queryset, estado, accion):
    n = errores = 0
    for r in queryset:
        if r.estado == estado:
            continue
        if estado in Reserva.ACTIVOS and not r.activa:
            try:
                verificar_reprogramacion(r, r.inicio, r.fin, r.mesa)
            except ErrorNegocio:
                errores += 1
                continue
        r.estado = estado
        registrar_historial(r, accion, f"por {request.user.get_username()}")
        try:
            with transaction.atomic():
                r.save(update_fields=["estado", "historial"])
        except IntegrityError:
            errores += 1
            continue
        n += 1
    modeladmin.message_user(request, f"{n} reserva(s) actualizada(s).", messages.SUCCESS)
    if errores:
        modeladmin.message_user(request, f"{errores} no se pudieron reactivar porque su horario ya está ocupado.", messages.WARNING)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    form = ReservaForm
    list_display = ["codigo", "estado_color", "fecha", "horario", "mesa", "nombre", "whatsapp", "valor", "origen"]
    list_filter = ["estado", "modalidad", "mesa", "origen", ("inicio", admin.DateFieldListFilter)]
    search_fields = ["codigo", "nombre", "celular", "correo", "observaciones"]
    ordering = ["-inicio"]
    list_select_related = ["mesa"]
    date_hierarchy = "inicio"
    readonly_fields = ["codigo", "creada_en", "historial_legible"]
    fieldsets = [
        (None, {"fields": ["codigo", "estado", "mesa", "modalidad", "inicio", "fin", "valor_estimado", "origen"]}),
        ("Cliente", {"fields": ["nombre", "celular", "correo"]}),
        ("Seguimiento", {"fields": ["observaciones", "historial_legible", "creada_en"]}),
    ]
    actions = ["confirmar", "marcar_en_curso", "finalizar", "cancelar", "rechazar", "exportar_csv"]
    list_per_page = 50

    def get_changeform_initial_data(self, request):
        datos = super().get_changeform_initial_data(request)
        datos.setdefault("origen", Reserva.Origen.PANEL)  # las reservas creadas a mano en el panel
        return datos

    @admin.action(description="Exportar seleccionadas a CSV (Excel)")
    def exportar_csv(self, request, qs):
        from .disponibilidad import BOGOTA

        filas = (
            (r.codigo, r.get_estado_display(), r.inicio.astimezone(BOGOTA).strftime("%Y-%m-%d"),
             r.inicio.astimezone(BOGOTA).strftime("%H:%M"), r.fin.astimezone(BOGOTA).strftime("%H:%M"),
             r.mesa.nombre, r.get_modalidad_display(), r.nombre, r.celular, r.correo, r.valor_estimado,
             r.get_origen_display(), r.observaciones, r.creada_en.astimezone(BOGOTA).strftime("%Y-%m-%d %H:%M"))
            for r in qs.select_related("mesa").order_by("inicio")
        )
        return respuesta_csv("reservas", ["Código", "Estado", "Fecha", "Inicio", "Fin", "Mesa", "Modalidad", "Nombre",
                                          "Celular", "Correo", "Valor estimado", "Origen", "Observaciones", "Creada"], filas)

    @admin.display(description="Estado", ordering="estado")
    def estado_color(self, obj):
        return insignia(obj.estado, obj.get_estado_display())

    @admin.display(description="Fecha", ordering="inicio")
    def fecha(self, obj):
        return fecha_corta(obj.inicio)

    @admin.display(description="Horario")
    def horario(self, obj):
        return f"{hora(obj.inicio)} – {hora(obj.fin)}"

    @admin.display(description="Celular")
    def whatsapp(self, obj):
        return enlace_whatsapp(obj.celular, f"Hola {obj.nombre}, te escribimos del {negocio.NOMBRE.valor} sobre tu reserva {obj.codigo}.")

    @admin.display(description="Valor")
    def valor(self, obj):
        return f"$ {obj.valor_estimado:,}".replace(",", ".") if obj.valor_estimado else "—"

    @admin.display(description="Historial")
    def historial_legible(self, obj):
        if not obj.historial:
            return "—"
        filas = format_html_join("", "<li>{} · {} {}</li>", ((h["fecha"][:16].replace("T", " "), h["accion"], h.get("detalle", "")) for h in obj.historial))
        return format_html("<ul style='margin:0;padding-left:16px'>{}</ul>", filas)

    def save_model(self, request, obj, form, change):
        if change and form.changed_data:
            registrar_historial(obj, "editada", ", ".join(form.changed_data) + f" · por {request.user.get_username()}")
        elif not change:
            registrar_historial(obj, "creada en el panel", f"por {request.user.get_username()}")
        try:
            with transaction.atomic():
                super().save_model(request, obj, form, change)
        except IntegrityError:
            self.message_user(request, "No se guardó: ese horario se cruza con otra reserva de la mesa.", messages.ERROR)

    @admin.action(description="Confirmar reservas seleccionadas")
    def confirmar(self, request, qs):
        _cambiar_estado(self, request, qs, Reserva.Estado.CONFIRMADA, "confirmada")

    @admin.action(description="Marcar como en curso")
    def marcar_en_curso(self, request, qs):
        _cambiar_estado(self, request, qs, Reserva.Estado.EN_CURSO, "en curso")

    @admin.action(description="Marcar como finalizadas")
    def finalizar(self, request, qs):
        _cambiar_estado(self, request, qs, Reserva.Estado.FINALIZADA, "finalizada")

    @admin.action(description="Cancelar reservas seleccionadas")
    def cancelar(self, request, qs):
        _cambiar_estado(self, request, qs, Reserva.Estado.CANCELADA, "cancelada")

    @admin.action(description="Rechazar (no aprobar)")
    def rechazar(self, request, qs):
        _cambiar_estado(self, request, qs, Reserva.Estado.RECHAZADA, "rechazada")


# ---------------------------------------------------------------- Escuela
@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]
    list_editable = ["activo"]


class SesionEnLinea(admin.TabularInline):
    model = SesionClase
    extra = 1
    fields = ["inicio", "cupos"]


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ["titulo", "modalidad", "nivel", "precio_txt", "confirmada", "activa", "orden"]
    list_editable = ["confirmada", "activa", "orden"]
    list_filter = ["modalidad", "nivel", "confirmada", "activa"]
    prepopulated_fields = {"slug": ["titulo"]}
    inlines = [SesionEnLinea]

    @admin.display(description="Precio")
    def precio_txt(self, obj):
        return f"$ {obj.precio:,}".replace(",", ".") if obj.precio else "Por confirmar"


def _padre(insc):
    """Horario de clase o torneo al que pertenece la inscripción: de ahí salen el cupo y la restricción de celular."""
    return insc.sesion if hasattr(insc, "sesion") else insc.torneo


def _motivo_bloqueo(modelo, campo, padre, celular, excluir_pk=None):
    """Razón por la que no se puede dejar una inscripción activa (cupo lleno o celular repetido); None si puede."""
    activas = modelo.objects.filter(**{campo: padre}).exclude(estado="cancelada")
    if excluir_pk:
        activas = activas.exclude(pk=excluir_pk)
    if activas.filter(celular=celular).exists():
        return "ese celular ya tiene otra inscripción activa en el mismo horario o torneo"
    if activas.count() >= padre.cupos:
        return f"no quedan cupos ({padre.cupos} de {padre.cupos} ocupados)"
    return None


def motivo_no_reactivable(insc):
    campo = "sesion" if hasattr(insc, "sesion") else "torneo"
    return _motivo_bloqueo(type(insc), campo, _padre(insc), insc.celular, insc.pk)


class InscripcionForm(forms.ModelForm):
    """Al editar en el panel no deja superar el cupo ni repetir celular (antes: error 500)."""

    def clean(self):
        datos = super().clean()
        campo = "sesion" if "sesion" in self.fields else "torneo"
        padre, celular, estado = datos.get(campo), datos.get("celular"), datos.get("estado")
        if padre and celular and estado and estado != "cancelada":
            motivo = _motivo_bloqueo(type(self.instance), campo, padre, celular, self.instance.pk)
            if motivo:
                raise forms.ValidationError(f"No se puede dejar la inscripción activa: {motivo}.")
        return datos


def _acciones_inscripcion(nombre_modelo):
    @admin.action(description=f"Confirmar {nombre_modelo} seleccionadas")
    def confirmar(modeladmin, request, qs):
        n = rechazadas = 0
        for insc in qs.select_related(*(["sesion"] if qs.model is InscripcionClase else ["torneo"])).order_by("creada_en"):
            if insc.estado == "confirmada":
                continue
            try:
                with transaction.atomic():
                    # Se bloquea la fila padre para que dos reactivaciones simultáneas no superen el cupo.
                    type(_padre(insc)).objects.select_for_update().get(pk=_padre(insc).pk)
                    if insc.estado == "cancelada":
                        motivo = motivo_no_reactivable(insc)
                        if motivo:
                            rechazadas += 1
                            modeladmin.message_user(request, f"{insc.codigo} · {insc.nombre}: no se reactivó, {motivo}.", messages.WARNING)
                            continue
                    insc.estado = "confirmada"
                    insc.save(update_fields=["estado"])
                    n += 1
            except IntegrityError:
                rechazadas += 1
                modeladmin.message_user(request, f"{insc.codigo} · {insc.nombre}: no se confirmó porque el celular ya está inscrito.", messages.WARNING)
        modeladmin.message_user(request, f"{n} inscripción(es) confirmada(s)." + (f" {rechazadas} no se pudieron confirmar." if rechazadas else ""),
                                messages.SUCCESS if n else messages.INFO)

    @admin.action(description=f"Cancelar {nombre_modelo} seleccionadas")
    def cancelar(modeladmin, request, qs):
        n = qs.exclude(estado="cancelada").update(estado="cancelada")
        modeladmin.message_user(request, f"{n} cancelada(s).", messages.SUCCESS)

    return [confirmar, cancelar]


@admin.register(InscripcionClase)
class InscripcionClaseAdmin(admin.ModelAdmin):
    form = InscripcionForm
    list_display = ["codigo", "estado_color", "sesion", "nombre", "whatsapp", "nivel_declarado", "creada_en"]
    list_filter = ["estado", "sesion__clase"]
    search_fields = ["codigo", "nombre", "celular", "correo"]
    readonly_fields = ["codigo", "creada_en"]
    actions = _acciones_inscripcion("inscripciones")

    @admin.display(description="Estado", ordering="estado")
    def estado_color(self, obj):
        return insignia(obj.estado, obj.get_estado_display())

    @admin.display(description="Celular")
    def whatsapp(self, obj):
        return enlace_whatsapp(obj.celular, f"Hola {obj.nombre}, te escribimos del club sobre tu inscripción {obj.codigo}.")


# ---------------------------------------------------------------- Torneos
class InscripcionTorneoEnLinea(admin.TabularInline):
    model = InscripcionTorneo
    extra = 0
    fields = ["codigo", "nombre", "celular", "estado"]
    readonly_fields = ["codigo"]


class PartidoEnLinea(admin.TabularInline):
    model = Partido
    extra = 0
    fields = ["ronda", "orden", "jugador_a", "marcador_a", "marcador_b", "jugador_b", "ganador"]
    ordering = ["ronda", "orden"]


@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "modalidad", "fecha", "estado", "publicado", "inscritos_txt"]
    list_filter = ["estado", "modalidad", "publicado"]
    list_editable = ["estado", "publicado"]
    prepopulated_fields = {"slug": ["nombre"]}
    inlines = [InscripcionTorneoEnLinea, PartidoEnLinea]
    actions = ["accion_generar_cuadro"]

    @admin.display(description="Inscritos")
    def inscritos_txt(self, obj):
        return f"{obj.inscritos} / {obj.cupos}"

    @admin.action(description="Generar cuadro con inscritos confirmados")
    def accion_generar_cuadro(self, request, qs):
        for t in qs:
            try:
                n = generar_cuadro(t)
                self.message_user(request, f"{t.nombre}: cuadro generado ({n} partidos en primera ronda).", messages.SUCCESS)
            except ErrorNegocio as e:
                self.message_user(request, f"{t.nombre}: {e.mensaje}", messages.ERROR)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        avanzar_ganadores(form.instance)  # los ganadores pasan solos a la siguiente ronda


@admin.register(InscripcionTorneo)
class InscripcionTorneoAdmin(admin.ModelAdmin):
    form = InscripcionForm
    list_display = ["codigo", "estado_color", "torneo", "nombre", "whatsapp", "creada_en"]
    list_filter = ["estado", "torneo"]
    search_fields = ["codigo", "nombre", "celular", "documento"]
    readonly_fields = ["codigo", "creada_en"]
    actions = _acciones_inscripcion("inscripciones")

    @admin.display(description="Estado", ordering="estado")
    def estado_color(self, obj):
        return insignia(obj.estado, obj.get_estado_display())

    @admin.display(description="Celular")
    def whatsapp(self, obj):
        return enlace_whatsapp(obj.celular, f"Hola {obj.nombre}, te escribimos del club sobre tu inscripción {obj.codigo}.")


# ---------------------------------------------------------------- Eventos, contacto y galería
@admin.register(SolicitudEvento)
class SolicitudEventoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "estado_color", "tipo", "fecha", "participantes", "nombre", "whatsapp", "empresa"]
    list_filter = ["estado", "tipo"]
    search_fields = ["codigo", "nombre", "celular", "empresa"]
    readonly_fields = ["codigo", "creada_en"]
    date_hierarchy = "fecha"

    @admin.display(description="Estado", ordering="estado")
    def estado_color(self, obj):
        return insignia(obj.estado, obj.get_estado_display())

    @admin.display(description="Celular")
    def whatsapp(self, obj):
        return enlace_whatsapp(obj.celular, f"Hola {obj.nombre}, te escribimos del club sobre tu solicitud de evento {obj.codigo}.")


@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "asunto", "correo", "celular", "leido", "creado_en"]
    list_filter = ["leido", "asunto"]
    search_fields = ["nombre", "correo", "mensaje"]
    readonly_fields = ["nombre", "correo", "celular", "asunto", "mensaje", "creado_en"]
    actions = ["marcar_leidos", "marcar_no_leidos", "exportar_csv"]
    date_hierarchy = "creado_en"
    ordering = ["leido", "-creado_en"]  # primero los pendientes por leer

    @admin.action(description="Marcar como leídos")
    def marcar_leidos(self, request, qs):
        self.message_user(request, f"{qs.update(leido=True)} mensaje(s) marcados como leídos.", messages.SUCCESS)

    @admin.action(description="Marcar como no leídos")
    def marcar_no_leidos(self, request, qs):
        self.message_user(request, f"{qs.update(leido=False)} mensaje(s) marcados como no leídos.", messages.SUCCESS)

    @admin.action(description="Exportar seleccionados a CSV (Excel)")
    def exportar_csv(self, request, qs):
        filas = ((m.creado_en.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M"), m.nombre, m.correo, m.celular,
                  m.get_asunto_display(), "Sí" if m.leido else "No", m.mensaje) for m in qs.order_by("creado_en"))
        return respuesta_csv("mensajes-contacto", ["Fecha", "Nombre", "Correo", "Celular", "Asunto", "Leído", "Mensaje"], filas)

    def has_add_permission(self, request):
        return False


@admin.register(FotoGaleria)
class FotoGaleriaAdmin(admin.ModelAdmin):
    list_display = ["miniatura", "alt", "categoria", "orden", "visible"]
    list_editable = ["categoria", "orden", "visible"]
    list_filter = ["categoria", "visible"]

    def has_add_permission(self, request):
        # En Vercel el disco es de solo lectura: las fotos nuevas se agregan al código (club/static).
        return not settings.EN_VERCEL

    def get_readonly_fields(self, request, obj=None):
        return ["imagen"] if settings.EN_VERCEL else []

    def miniatura(self, obj):
        return format_html('<img src="{}" style="height:56px;border-radius:6px">', obj.url) if obj.url else "—"


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ["titulo", "vigencia", "destacada", "activa", "orden", "es_ejemplo"]
    list_editable = ["destacada", "activa", "orden"]
    list_filter = ["activa", "destacada"]
    search_fields = ["titulo", "descripcion"]
    fieldsets = [
        (None, {"fields": ["titulo", "descripcion", "activa", "destacada", "orden"],
                "description": "Solo se muestran en la web las promociones activas y vigentes (máximo 3, por orden)."}),
        ("Vigencia (opcional)", {"fields": ["vigencia_desde", "vigencia_hasta"]}),
        ("Botón (opcional)", {"fields": ["enlace_url", "enlace_texto"]}),
    ]

    @admin.display(description="Vigencia")
    def vigencia(self, obj):
        return obj.vigencia_texto or "Sin fechas"

    @admin.display(description="Demo", boolean=True)
    def es_ejemplo(self, obj):
        return obj.ejemplo
