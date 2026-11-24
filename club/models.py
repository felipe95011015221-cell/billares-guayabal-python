"""Modelos de datos del Club de Billares Guayabal."""
import secrets
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from . import negocio

ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I/L


def generar_codigo(prefijo: str, largo: int = 6) -> str:
    return f"{prefijo}-" + "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(largo))


MAX_IMAGEN_BYTES = 5 * 1024 * 1024  # 5 MB por foto


def validar_tamano_imagen(archivo):
    """Rechaza fotos demasiado pesadas (el disco y el ancho de banda del hosting son limitados)."""
    if archivo and getattr(archivo, "size", 0) > MAX_IMAGEN_BYTES:
        raise ValidationError(f"La imagen pesa {archivo.size / 1048576:.1f} MB; el máximo es {MAX_IMAGEN_BYTES // 1048576} MB.")


MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_es(d: date, con_anio: bool = False) -> str:
    return f"{d.day} de {MESES_ES[d.month - 1]}" + (f" de {d.year}" if con_anio else "")


class Modalidad(models.TextChoices):
    CARAMBOLA = "carambola", "Carambola a tres bandas"
    POOL = "pool", "Pool"


# ---------------------------------------------------------------- Ajustes
class Ajustes(models.Model):
    """Fila única con las políticas editables desde el panel."""

    class Modo(models.TextChoices):
        MANUAL = "manual", "Manual · el club confirma cada solicitud"
        AUTOMATICA = "automatica", "Automática · se confirma al reservar"

    modo_reserva = models.CharField("modo de confirmación", max_length=12, choices=Modo.choices, default=Modo.MANUAL)
    duraciones = models.JSONField("duraciones permitidas (minutos)", default=list, help_text="Ej.: [60, 90, 120, 180]")
    intervalo_min = models.PositiveSmallIntegerField("intervalo entre horas de inicio (min)", default=30)
    anticipacion_min = models.PositiveIntegerField("anticipación mínima (min)", default=60)
    dias_max = models.PositiveSmallIntegerField("días máximos de anticipación", default=30)
    hora_apertura = models.PositiveSmallIntegerField("apertura (minutos desde 00:00)", default=negocio.APERTURA_MIN)
    hora_cierre = models.PositiveSmallIntegerField("cierre (minutos; 1560 = 2:00 a. m.)", default=negocio.CIERRE_MIN)
    politica = models.TextField(
        "política de reservas",
        default=(
            "Las reservas en línea son solicitudes sujetas a confirmación del club. Te contactaremos por WhatsApp o llamada "
            "para confirmarla. Si no puedes asistir, avísanos con anticipación para liberar la mesa. La mesa puede liberarse "
            "si no te presentas dentro de los primeros 15 minutos."
        ),
    )
    texto_hero = models.CharField("título del inicio", max_length=120, blank=True)
    subtitulo_hero = models.CharField("subtítulo del inicio", max_length=240, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "configuración"

    def __str__(self):
        return "Configuración del club"

    def clean(self):
        from django.core.exceptions import ValidationError

        errores = {}
        if self.intervalo_min < 5:
            errores["intervalo_min"] = "Debe ser de al menos 5 minutos."
        if self.hora_cierre <= self.hora_apertura:
            errores["hora_cierre"] = "El cierre debe ser posterior a la apertura."
        if not (isinstance(self.duraciones, list) and self.duraciones
                and all(isinstance(d, int) and not isinstance(d, bool) and 15 <= d <= 600 for d in self.duraciones)):
            errores["duraciones"] = "Escribe una lista de minutos entre 15 y 600, por ejemplo [60, 90, 120]."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.pk = 1
        if not self.duraciones:
            self.duraciones = [60, 90, 120, 180]
        super().save(*args, **kwargs)

    @classmethod
    def actual(cls) -> "Ajustes":
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"duraciones": [60, 90, 120, 180]})
        return obj


# ---------------------------------------------------------------- Mesas
class Mesa(models.Model):
    nombre = models.CharField(max_length=40)
    modalidad = models.CharField(max_length=12, choices=Modalidad.choices)
    tarifa_hora = models.PositiveIntegerField("tarifa por hora (COP)", null=True, blank=True, help_text="Vacío = «Tarifa por confirmar»")
    activa = models.BooleanField(default=True)
    mantenimiento = models.BooleanField("en mantenimiento", default=False)
    notas = models.CharField(max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name_plural = "mesas"

    def __str__(self):
        return f"{self.nombre} · {self.get_modalidad_display()}"


class Bloqueo(models.Model):
    class Tipo(models.TextChoices):
        BLOQUEO = "bloqueo", "Bloqueo"
        OCUPADA = "ocupada", "Ocupada (cliente sin reserva)"
        MANTENIMIENTO = "mantenimiento", "Mantenimiento"

    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, related_name="bloqueos")
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    tipo = models.CharField(max_length=14, choices=Tipo.choices, default=Tipo.BLOQUEO)
    motivo = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["inicio"]
        constraints = [models.CheckConstraint(condition=models.Q(fin__gt=models.F("inicio")), name="bloqueo_fin_despues_inicio")]

    def __str__(self):
        return f"{self.mesa.nombre} · {self.get_tipo_display()}"


# ---------------------------------------------------------------- Reservas
class Reserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Solicitud pendiente de confirmación"
        CONFIRMADA = "confirmada", "Confirmada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"
        CANCELADA = "cancelada", "Cancelada"
        RECHAZADA = "rechazada", "No aprobada"

    class Origen(models.TextChoices):
        WEB = "web", "Sitio web"
        PANEL = "panel", "Panel (manual)"
        WHATSAPP = "whatsapp", "WhatsApp"
        TELEFONO = "telefono", "Llamada"
        PRESENCIAL = "presencial", "En el club"

    ACTIVOS = (Estado.PENDIENTE, Estado.CONFIRMADA, Estado.EN_CURSO)

    codigo = models.CharField(max_length=12, unique=True, editable=False)
    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, related_name="reservas")
    modalidad = models.CharField(max_length=12, choices=Modalidad.choices)
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    nombre = models.CharField(max_length=80)
    celular = models.CharField(max_length=10)
    correo = models.EmailField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    valor_estimado = models.PositiveIntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    origen = models.CharField(
        "origen", max_length=10, choices=Origen.choices, default="web", blank=True,
        help_text="Por dónde llegó la reserva (para medir qué canal funciona).",
    )
    historial = models.JSONField(default=list, blank=True, editable=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["inicio"]
        constraints = [models.CheckConstraint(condition=models.Q(fin__gt=models.F("inicio")), name="reserva_fin_despues_inicio")]
        indexes = [models.Index(fields=["inicio"]), models.Index(fields=["mesa", "inicio"])]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo("BG")
        super().save(*args, **kwargs)

    @property
    def activa(self) -> bool:
        return self.estado in self.ACTIVOS


# ---------------------------------------------------------------- Escuela
class Instructor(models.Model):
    nombre = models.CharField(max_length=80)
    bio = models.TextField("perfil", blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "instructores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Clase(models.Model):
    class Nivel(models.TextChoices):
        INICIACION = "Iniciación"
        BASICO = "Básico"
        INTERMEDIO = "Intermedio"
        AVANZADO = "Avanzado"
        TODOS = "Todos los niveles"

    class ModalidadClase(models.TextChoices):
        AMBAS = "ambas", "Carambola y pool"
        CARAMBOLA = "carambola", "Carambola"
        POOL = "pool", "Pool"

    slug = models.SlugField(unique=True, blank=True)
    titulo = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    modalidad = models.CharField(max_length=10, choices=ModalidadClase.choices, default=ModalidadClase.AMBAS)
    nivel = models.CharField(max_length=20, choices=Nivel.choices, default=Nivel.INICIACION)
    duracion_min = models.PositiveSmallIntegerField("duración (min)", default=60, validators=[MinValueValidator(15)])
    instructor = models.ForeignKey(Instructor, null=True, blank=True, on_delete=models.SET_NULL)
    precio = models.PositiveIntegerField("precio (COP)", null=True, blank=True, help_text="Vacío = «Por confirmar»")
    confirmada = models.BooleanField("confirmada por el club", default=False, help_text="Si no, se muestra como «Programa propuesto»")
    activa = models.BooleanField("visible en la web", default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)[:50]
        super().save(*args, **kwargs)


class SesionClase(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="sesiones")
    inicio = models.DateTimeField()
    cupos = models.PositiveSmallIntegerField(default=6, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["inicio"]
        verbose_name = "horario de clase"
        verbose_name_plural = "horarios de clase"

    def __str__(self):
        return f"{self.clase} · {self.inicio:%d/%m %H:%M}"

    def ocupados(self) -> int:
        return self.inscripciones.exclude(estado=InscripcionClase.Estado.CANCELADA).count()


class InscripcionClase(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"

    codigo = models.CharField(max_length=12, unique=True, editable=False)
    sesion = models.ForeignKey(SesionClase, on_delete=models.CASCADE, related_name="inscripciones")
    nombre = models.CharField(max_length=80)
    celular = models.CharField(max_length=10)
    correo = models.EmailField()
    nivel_declarado = models.CharField(max_length=60, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada_en"]
        verbose_name = "inscripción a clase"
        verbose_name_plural = "inscripciones a clases"
        constraints = [
            models.UniqueConstraint(fields=["sesion", "celular"], condition=~models.Q(estado="cancelada"), name="inscripcion_clase_unica"),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo("CL")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


# ---------------------------------------------------------------- Torneos
class Torneo(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ABIERTO = "inscripciones_abiertas", "Inscripciones abiertas"
        CERRADO = "inscripciones_cerradas", "Inscripciones cerradas"
        EN_JUEGO = "en_juego", "En juego"
        FINALIZADO = "finalizado", "Finalizado"
        CANCELADO = "cancelado", "Cancelado"

    slug = models.SlugField(unique=True, blank=True)
    nombre = models.CharField(max_length=120)
    modalidad = models.CharField(max_length=12, choices=Modalidad.choices, default=Modalidad.CARAMBOLA)
    fecha = models.DateTimeField()
    formato = models.CharField(max_length=200, blank=True)
    requisitos = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
    valor_inscripcion = models.PositiveIntegerField("valor de inscripción (COP)", null=True, blank=True)
    cupos = models.PositiveSmallIntegerField(default=16, validators=[MinValueValidator(2)])
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.BORRADOR)
    publicado = models.BooleanField("publicado (aprobado por el club)", default=False)

    class Meta:
        ordering = ["fecha"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.nombre}-{self.fecha:%Y-%m-%d}")[:50]
        super().save(*args, **kwargs)

    def inscritos(self) -> int:
        return self.inscripciones.exclude(estado=InscripcionTorneo.Estado.CANCELADA).count()


class InscripcionTorneo(models.Model):
    Estado = InscripcionClase.Estado

    codigo = models.CharField(max_length=12, unique=True, editable=False)
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="inscripciones")
    nombre = models.CharField(max_length=80)
    celular = models.CharField(max_length=10)
    correo = models.EmailField()
    documento = models.CharField(max_length=20, blank=True)
    estado = models.CharField(max_length=12, choices=InscripcionClase.Estado.choices, default="pendiente")
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creada_en"]
        verbose_name = "inscripción a torneo"
        verbose_name_plural = "inscripciones a torneos"
        constraints = [
            models.UniqueConstraint(fields=["torneo", "celular"], condition=~models.Q(estado="cancelada"), name="inscripcion_torneo_unica"),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo("TG")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Partido(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="partidos")
    ronda = models.PositiveSmallIntegerField()
    orden = models.PositiveSmallIntegerField()
    jugador_a = models.CharField(max_length=80, blank=True)
    jugador_b = models.CharField(max_length=80, blank=True)
    marcador_a = models.PositiveSmallIntegerField(null=True, blank=True)
    marcador_b = models.PositiveSmallIntegerField(null=True, blank=True)
    ganador = models.CharField(max_length=1, choices=[("A", "A"), ("B", "B")], blank=True)

    class Meta:
        ordering = ["ronda", "orden"]

    def __str__(self):
        return f"R{self.ronda} · {self.jugador_a or '—'} vs {self.jugador_b or '—'}"


# ---------------------------------------------------------------- Eventos y contacto
class SolicitudEvento(models.Model):
    class Tipo(models.TextChoices):
        PRIVADO = "privado", "Evento privado"
        EMPRESARIAL = "empresarial", "Encuentro empresarial"
        CELEBRACION = "celebracion", "Celebración"
        RECREATIVO = "recreativo", "Jornada recreativa"
        GRUPAL = "grupal", "Actividad grupal"

    class Estado(models.TextChoices):
        NUEVA = "nueva", "Nueva"
        REVISION = "en_revision", "En revisión"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"
        CERRADA = "cerrada", "Cerrada"

    codigo = models.CharField(max_length=12, unique=True, editable=False)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    fecha = models.DateField()
    participantes = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=80)
    celular = models.CharField(max_length=10)
    correo = models.EmailField()
    empresa = models.CharField(max_length=80, blank=True)
    mensaje = models.TextField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.NUEVA)
    notas = models.TextField("notas internas", blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada_en"]
        verbose_name = "solicitud de evento"
        verbose_name_plural = "solicitudes de eventos"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo("EV")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} · {self.get_tipo_display()}"


class MensajeContacto(models.Model):
    class Asunto(models.TextChoices):
        RESERVAS = "reservas", "Reservas"
        CLASES = "clases", "Clases"
        TORNEOS = "torneos", "Torneos"
        EVENTOS = "eventos", "Eventos"
        OTRO = "otro", "Otro"

    nombre = models.CharField(max_length=80)
    correo = models.EmailField()
    celular = models.CharField(max_length=20, blank=True)
    asunto = models.CharField(max_length=10, choices=Asunto.choices)
    mensaje = models.TextField()
    leido = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "mensaje de contacto"
        verbose_name_plural = "mensajes de contacto"

    def __str__(self):
        return f"{self.nombre} · {self.get_asunto_display()}"


# ---------------------------------------------------------------- Galería
class FotoGaleria(models.Model):
    class Categoria(models.TextChoices):
        CARAMBOLA = "carambola", "Carambola"
        POOL = "pool", "Pool"
        AMBIENTE = "ambiente", "Ambiente"
        DETALLE = "detalle", "Detalle"

    imagen = models.ImageField(
        upload_to="galeria/", blank=True, help_text="Sube una foto real del club (JPG, PNG o WebP, máximo 5 MB)",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validar_tamano_imagen],
    )
    ruta_estatica = models.CharField(max_length=200, blank=True, editable=False, help_text="Fotos incluidas con el sitio")
    alt = models.CharField("descripción (texto alternativo)", max_length=160)
    categoria = models.CharField(max_length=10, choices=Categoria.choices, default=Categoria.AMBIENTE)
    ancho = models.PositiveIntegerField(default=1600, editable=False)
    alto = models.PositiveIntegerField(default=1200, editable=False)
    orden = models.IntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "foto de la galería"
        verbose_name_plural = "galería"

    def __str__(self):
        return self.alt

    @property
    def url(self) -> str:
        from django.templatetags.static import static

        return self.imagen.url if self.imagen else static(f"club/img/{self.ruta_estatica}")


# ---------------------------------------------------------------- Promociones
class PromocionQuerySet(models.QuerySet):
    def vigentes(self, hoy: date | None = None):
        """Activas y dentro de su vigencia (sin fechas = siempre vigente)."""
        if hoy is None:
            from .disponibilidad import hoy_bogota

            hoy = hoy_bogota()
        return self.filter(activa=True).filter(
            models.Q(vigencia_desde__isnull=True) | models.Q(vigencia_desde__lte=hoy),
            models.Q(vigencia_hasta__isnull=True) | models.Q(vigencia_hasta__gte=hoy),
        )


class Promocion(models.Model):
    titulo = models.CharField(max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    vigencia_desde = models.DateField("vigente desde", null=True, blank=True)
    vigencia_hasta = models.DateField("vigente hasta (inclusive)", null=True, blank=True)
    destacada = models.BooleanField(default=False)
    activa = models.BooleanField("visible en la web", default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    enlace_url = models.CharField("enlace del botón", max_length=200, blank=True, help_text="Ruta interna (/reservas/) o enlace completo (https://...)")
    enlace_texto = models.CharField("texto del botón", max_length=40, blank=True)
    ejemplo = models.BooleanField("es un ejemplo de demostración", default=False, editable=False)

    objects = PromocionQuerySet.as_manager()

    class Meta:
        ordering = ["orden", "-destacada", "id"]
        verbose_name = "promoción"
        verbose_name_plural = "promociones"

    def __str__(self):
        return self.titulo

    def clean(self):
        if self.vigencia_desde and self.vigencia_hasta and self.vigencia_hasta < self.vigencia_desde:
            raise ValidationError({"vigencia_hasta": "La fecha final no puede ser anterior a la inicial."})
        if self.enlace_url and not self.enlace_url.startswith(("/", "https://", "http://")):
            raise ValidationError({"enlace_url": "Usa una ruta que empiece por / o un enlace completo (https://...)."})

    @property
    def vigencia_texto(self) -> str:
        d, h = self.vigencia_desde, self.vigencia_hasta
        if d and h:
            if d == h:
                return f"Solo el {_fecha_es(d, True)}"
            if d.year == h.year:
                return f"Del {_fecha_es(d)} al {_fecha_es(h, True)}"
            return f"Del {_fecha_es(d, True)} al {_fecha_es(h, True)}"
        if h:
            return f"Hasta el {_fecha_es(h, True)}"
        if d:
            return f"Desde el {_fecha_es(d, True)}"
        return ""
