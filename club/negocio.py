"""
CONFIGURACIÓN CENTRAL DEL NEGOCIO — Club de Billares Guayabal.

Cada dato tiene un estado de verificación:
  "confirmado": validado por el propietario (entra en los datos estructurados de Google).
  "publico":    encontrado en fuentes públicas, pendiente de validar (se muestra «por confirmar»).
  "pendiente":  no hay dato.

Tarifas, mesas, clases, horarios y políticas se editan desde el panel /admin.
"""
from dataclasses import dataclass, field
from urllib.parse import quote


@dataclass(frozen=True)
class Dato:
    valor: str
    estado: str = "pendiente"
    fuente: str = ""

    @property
    def confirmado(self) -> bool:
        return self.estado == "confirmado"

    @property
    def por_confirmar(self) -> bool:
        return self.estado != "confirmado"


NOMBRE = Dato("Club de Billares Guayabal", "confirmado", "Confirmado por el cliente junto con el logo oficial (19 nov. 2026)")
NOMBRE_CORTO = "Club de Billares Guayabal"
CIUDAD = Dato("Medellín", "confirmado")
REGION = "Antioquia"
PAIS = "CO"
DIRECCION = Dato("Carrera 52 #9-17, Guayabal, Medellín", "publico", "Dato público del brief; no contrastado con otra fuente.")
TELEFONO = Dato("+57 314 773 0533", "publico", "Dato público del brief, pendiente de validación.")
TELEFONO_E164 = "573147730533"
CORREO = Dato("", "pendiente")
HORARIO = Dato("Todos los días, 9:00 a. m. – 2:00 a. m.", "publico", "Horario reportado en plataformas públicas.")
INSTAGRAM = Dato("", "pendiente")
FACEBOOK = Dato("", "pendiente")
MAPA_CONSULTA = "Carrera 52 #9-17, Guayabal, Medellín, Antioquia, Colombia"

# Horario operativo por defecto del motor de reservas (minutos desde las 00:00; 26:00 = 2:00 a. m.).
APERTURA_MIN = 9 * 60
CIERRE_MIN = 26 * 60


def datos_pendientes():
    campos = [
        ("Dirección", DIRECCION), ("Teléfono / WhatsApp", TELEFONO), ("Correo electrónico", CORREO),
        ("Horario", HORARIO), ("Instagram", INSTAGRAM), ("Facebook", FACEBOOK),
    ]
    return [{"campo": c, "valor": d.valor or "—", "estado": d.estado} for c, d in campos if d.por_confirmar]


# ---------- WhatsApp, llamadas y mapas ----------
MENSAJES_WHATSAPP = {
    "general": "Hola, Club de Billares Guayabal. Quisiera más información sobre el club.",
    "reservas": "Hola, Club de Billares Guayabal. Quisiera reservar una mesa. ¿Me ayudan con la disponibilidad?",
    "clases": "Hola, Club de Billares Guayabal. Me interesan las clases de billar. ¿Qué programas y horarios tienen?",
    "torneos": "Hola, Club de Billares Guayabal. Quisiera información sobre los próximos torneos y cómo inscribirme.",
    "eventos": "Hola, Club de Billares Guayabal. Quisiera cotizar un evento en el club.",
    "ubicacion": "Hola, Club de Billares Guayabal. ¿Me confirman la dirección y cómo llegar?",
}


def enlace_whatsapp(contexto: str = "general", extra: str = "") -> str:
    texto = MENSAJES_WHATSAPP.get(contexto, MENSAJES_WHATSAPP["general"])
    if extra:
        texto = f"{texto}\n\n{extra}"
    return f"https://wa.me/{TELEFONO_E164}?text={quote(texto)}"


def enlace_compartir_whatsapp(texto: str) -> str:
    return f"https://wa.me/?text={quote(texto)}"


ENLACE_LLAMAR = f"tel:+{TELEFONO_E164}"
ENLACE_MAPA = f"https://www.google.com/maps/search/?api=1&query={quote(MAPA_CONSULTA)}"
ENLACE_COMO_LLEGAR = f"https://www.google.com/maps/dir/?api=1&destination={quote(MAPA_CONSULTA)}"
ENLACE_MAPA_EMBEBIDO = f"https://www.google.com/maps?q={quote(MAPA_CONSULTA)}&output=embed"

NAV = [
    ("club", "El club"), ("reservas", "Reservas"), ("escuela", "Escuela"), ("torneos", "Torneos"),
    ("eventos", "Eventos"), ("galeria", "Galería"), ("contacto", "Contacto"),
]


# ---------- Fotos ----------
@dataclass(frozen=True)
class Foto:
    archivo: str  # ruta dentro de static/club/img/
    alt: str
    ancho: int
    alto: int
    categoria: str = "ambiente"
    autor: str = ""
    fuente: str = ""
    url_fuente: str = ""

    @property
    def es_referencia(self) -> bool:
        return bool(self.fuente)

    @property
    def licencia(self) -> str:
        return {"Unsplash": "Licencia Unsplash", "Pexels": "Licencia Pexels"}.get(self.fuente, "")

    @property
    def url_licencia(self) -> str:
        return {"Unsplash": "https://unsplash.com/license", "Pexels": "https://www.pexels.com/license/"}.get(self.fuente, "")


U, P = "Unsplash", "Pexels"
FOTOS = {
    "hero_salon": Foto("hero-salon.webp", "Salón de billar en penumbra con bolas y un taco sobre el paño", 2400, 1600, "ambiente", "Wecko Helios", U, "https://unsplash.com/photos/DObE_YU6oks"),
    "bolas_bokeh": Foto("bolas-bokeh.webp", "Bolas de pool en primer plano con luces cálidas al fondo", 2400, 1600, "pool", "Christian Wiediger", U, "https://unsplash.com/photos/QnDhG4nNCVQ"),
    "tres_bolas": Foto("tres-bolas.webp", "Tres bolas junto a la buchaca de una mesa de fieltro verde", 1600, 2387, "detalle", "Maximilian Bungart", U, "https://unsplash.com/photos/S4iH6Yso6cs"),
    "tiro_mesa_verde": Foto("tiro-mesa-verde.webp", "Vista cenital de un tiro con taco sobre una mesa verde", 2400, 1600, "pool", "cal gao", U, "https://unsplash.com/photos/yV5awvq2hiI"),
    "mano_taco": Foto("mano-taco.webp", "Mano formando el puente con el taco frente a la bola blanca", 1600, 2413, "detalle", "Valeria Kodra", U, "https://unsplash.com/photos/2SiUvKOT6Cg"),
    "triangulo_bolas": Foto("triangulo-bolas.webp", "Bolas numeradas ordenadas dentro de un triángulo de madera", 2400, 1600, "detalle", "gladys rovetta", U, "https://unsplash.com/photos/Xpo7AhoJdNM"),
    "mesa_azul_tacos": Foto("mesa-azul-tacos.webp", "Mesa de paño azul con dos tacos y el triángulo armado", 2400, 1800, "detalle", "Saint Rambo", U, "https://unsplash.com/photos/BhvoOhQMv5I"),
    "triangulo_tacos": Foto("triangulo-tacos.webp", "Tacos cruzados sobre el triángulo de bolas listo para el saque", 2400, 1537, "detalle", "Marcelo Leal", U, "https://unsplash.com/photos/6UeBe2HqziA"),
    "salon_mesas": Foto("salon-mesas.webp", "Hilera de mesas de billar iluminadas en un salón oscuro", 2400, 1600, "ambiente", "Vazha Despotashvili", P, "https://www.pexels.com/photo/blue-billiard-tables-6032656/"),
    "jugador_salon": Foto("jugador-salon.webp", "Jugador apuntando en una mesa grande bajo lámparas colgantes", 2400, 1600, "ambiente", "Tima Miroshnichenko", P, "https://www.pexels.com/photo/a-man-playing-billiard-6254197/"),
}
FOTOS_REFERENCIA = list(FOTOS.values())

# Fotos reales del club
JUGADOR_ESTUDIO = Foto("club/jugador-estudio.webp", "Jugador de camiseta naranja concentrado mientras apunta su tiro sobre una mesa de paño azul", 1554, 1204, "carambola")
FOTOS_INICIO = [
    Foto("club/salon-mesas-carambola.webp", "Salón del Club de Billares Guayabal con mesas de carambola de paño azul y jugadores al fondo", 960, 1200, "carambola"),
    Foto("club/mesa-carambola-detalle.webp", "Mesa de carambola del club en primer plano con bolas blanca y roja sobre el paño azul", 960, 1200, "carambola"),
]
GALERIA_INICIAL = [
    Foto("club/salon-panoramico.webp", "Vista desde el segundo piso del salón del Club de Billares Guayabal con sus mesas de carambola en juego", 913, 1220, "ambiente"),
    FOTOS_INICIO[0],
    Foto("club/salon-vista-alta-dia.webp", "Jugadores en las mesas de carambola de paño azul vistas desde el balcón del club", 913, 1220, "carambola"),
    Foto("club/mesas-en-juego.webp", "Fila de mesas de carambola con partidas en curso en el salón del club", 913, 1220, "carambola"),
    FOTOS_INICIO[1],
    Foto("club/salon-vista-alta-noche.webp", "El salón de noche con todas las mesas ocupadas y el mural de campeones en la pared", 913, 512, "ambiente"),
    Foto("club/bar-del-club.webp", "Barra del club con clientes sentados y estantería iluminada en tonos morados", 913, 682, "ambiente"),
]


@dataclass(frozen=True)
class Video:
    archivo: str
    portada: str
    ancho: int
    alto: int
    fecha: str
    titulo: str
    descripcion: str
    duracion: str = ""


VIDEO_EVENTO = Video(
    archivo="videos/evento-2026-11-21.mp4",
    portada="videos/evento-2026-11-21-portada.webp",
    ancho=478, alto=850, duracion="1:52",
    fecha="Sábado 21 de noviembre de 2026",
    titulo="Así se vivió nuestro último evento",
    descripcion=(
        "Buena comida, partidas en todas las mesas, la barra llena y mucha gente compartiendo. "
        "Ese es el ambiente del Club de Billares Guayabal: respeto, buena actitud y amor por el billar."
    ),
)
