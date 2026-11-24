"""Validación en el servidor de todos los formularios públicos (equivalente a los esquemas Zod)."""
import re

from django import forms
from django.core.exceptions import ValidationError

from .models import MensajeContacto, Modalidad, SolicitudEvento

MSG_NOMBRE = "Escribe tu nombre completo."
MSG_CELULAR = "Ingresa un celular colombiano de 10 dígitos (ej. 3001234567)."
MSG_CORREO = "Ingresa un correo válido."
MSG_DATOS = "Debes autorizar el tratamiento de datos personales."


def normalizar_celular(valor: str) -> str:
    d = re.sub(r"\D", "", valor or "")
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    return d


class FormBase(forms.Form):
    """Campos comunes: nombre, celular, correo, autorización y campo trampa anti-spam."""

    nombre = forms.CharField(min_length=3, max_length=80, error_messages={"required": MSG_NOMBRE, "min_length": MSG_NOMBRE})
    celular = forms.CharField(max_length=20, error_messages={"required": MSG_CELULAR})
    correo = forms.EmailField(max_length=120, error_messages={"required": MSG_CORREO, "invalid": MSG_CORREO})
    acepta_datos = forms.BooleanField(error_messages={"required": MSG_DATOS})
    website = forms.CharField(required=False)  # honeypot: las personas lo dejan vacío

    def clean_nombre(self):
        return self.cleaned_data["nombre"].strip()

    def clean_celular(self):
        c = normalizar_celular(self.cleaned_data["celular"])
        if not re.fullmatch(r"3\d{9}", c):
            raise ValidationError(MSG_CELULAR)
        return c

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("Solicitud no válida.")
        return ""


MSG_MODALIDAD = {"required": "Elige carambola o pool.", "invalid_choice": "Elige carambola o pool."}
MSG_FECHA = {"required": "Elige una fecha.", "invalid": "La fecha no es válida."}
MSG_DURACION = {"required": "Elige una duración.", "invalid": "La duración no es válida.",
                "min_value": "La duración no es válida.", "max_value": "La duración no es válida."}
MSG_INICIO = {"required": "Elige una hora de inicio.", "invalid": "La hora de inicio no es válida.",
              "min_value": "La hora de inicio no es válida.", "max_value": "La hora de inicio no es válida."}


class ConsultaDisponibilidadForm(forms.Form):
    modalidad = forms.ChoiceField(choices=Modalidad.choices, error_messages=MSG_MODALIDAD)
    fecha = forms.DateField(input_formats=["%Y-%m-%d"], error_messages=MSG_FECHA)
    duracion = forms.IntegerField(min_value=15, max_value=600, error_messages=MSG_DURACION)
    inicio = forms.IntegerField(min_value=0, max_value=48 * 60, required=False, error_messages=MSG_INICIO)


class ReservaForm(FormBase):
    modalidad = forms.ChoiceField(choices=Modalidad.choices, error_messages=MSG_MODALIDAD)
    fecha = forms.DateField(input_formats=["%Y-%m-%d"], error_messages=MSG_FECHA)
    inicio = forms.IntegerField(min_value=0, max_value=48 * 60, error_messages=MSG_INICIO)
    duracion = forms.IntegerField(min_value=15, max_value=600, error_messages=MSG_DURACION)
    mesa_id = forms.IntegerField(error_messages={"required": "Selecciona una mesa."})


class ConsultaReservaForm(forms.Form):
    codigo = forms.CharField(max_length=12)
    celular = forms.CharField(max_length=20)

    def clean_codigo(self):
        c = self.cleaned_data["codigo"].strip().upper()
        if not re.fullmatch(r"BG-[A-Z0-9]{6}", c):
            raise ValidationError("El código tiene el formato BG-XXXXXX.")
        return c

    def clean_celular(self):
        c = normalizar_celular(self.cleaned_data["celular"])
        if not re.fullmatch(r"3\d{9}", c):
            raise ValidationError(MSG_CELULAR)
        return c


class InscripcionClaseForm(FormBase):
    sesion_id = forms.IntegerField(error_messages={"required": "Selecciona un horario."})
    nivel_declarado = forms.CharField(max_length=60, required=False)


class InscripcionTorneoForm(FormBase):
    torneo_id = forms.IntegerField()
    documento = forms.CharField(max_length=20, required=False)
    acepta_reglamento = forms.BooleanField(error_messages={"required": "Debes aceptar los requisitos del torneo."})


class SolicitudEventoForm(FormBase):
    tipo = forms.ChoiceField(choices=SolicitudEvento.Tipo.choices)
    fecha = forms.DateField(input_formats=["%Y-%m-%d"])
    participantes = forms.IntegerField(
        min_value=2, max_value=300,
        error_messages={"min_value": "Mínimo 2 participantes.", "max_value": "Para grupos más grandes, escríbenos."},
    )
    empresa = forms.CharField(max_length=80, required=False)
    mensaje = forms.CharField(max_length=1000, required=False)

    def clean_fecha(self):
        from .disponibilidad import hoy_bogota

        f = self.cleaned_data["fecha"]
        if f <= hoy_bogota():
            raise ValidationError("Elige una fecha futura.")
        return f


class ContactoForm(forms.Form):
    nombre = forms.CharField(min_length=3, max_length=80, error_messages={"required": MSG_NOMBRE, "min_length": MSG_NOMBRE})
    correo = forms.EmailField(max_length=120, error_messages={"required": MSG_CORREO, "invalid": MSG_CORREO})
    celular = forms.CharField(max_length=20, required=False)
    asunto = forms.ChoiceField(choices=MensajeContacto.Asunto.choices)
    mensaje = forms.CharField(min_length=10, max_length=1500, error_messages={"min_length": "Cuéntanos un poco más (mínimo 10 caracteres)."})
    acepta_datos = forms.BooleanField(error_messages={"required": MSG_DATOS})
    website = forms.CharField(required=False)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("Solicitud no válida.")
        return ""
