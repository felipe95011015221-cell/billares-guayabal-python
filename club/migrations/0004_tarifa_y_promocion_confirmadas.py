"""
Datos confirmados por el propietario (23 nov. 2026), cargados UNA sola vez:

- Tarifa por hora de las mesas: COP 15.000. Solo se asigna a las mesas que no tienen tarifa,
  así que no pisa lo que el club ya haya editado en el panel.
- Promoción «La hora de billar a tres bandas, a $ 7.500», antes de las 3 p. m. de lunes a viernes.
  Se crea si no existe una con ese título. Después se administra desde el panel (editar, desactivar o borrar):
  como es una migración, no se vuelve a crear en los siguientes despliegues.
"""
from django.db import migrations

TARIFA_HORA = 15000
TITULO_PROMOCION = "La hora de billar a tres bandas, a $ 7.500"


def cargar(apps, schema_editor):
    Mesa = apps.get_model("club", "Mesa")
    Promocion = apps.get_model("club", "Promocion")
    Mesa.objects.filter(tarifa_hora__isnull=True).update(tarifa_hora=TARIFA_HORA)
    if not Promocion.objects.filter(titulo=TITULO_PROMOCION).exists():
        Promocion.objects.create(
            titulo=TITULO_PROMOCION,
            descripcion="Antes de las 3 p. m., de lunes a viernes.",
            destacada=True,
            activa=True,
            orden=0,
            enlace_url="/reservas/?modalidad=carambola",
            enlace_texto="Reservar mesa de carambola",
        )


class Migration(migrations.Migration):
    dependencies = [("club", "0003_promociones_origen_reserva")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
