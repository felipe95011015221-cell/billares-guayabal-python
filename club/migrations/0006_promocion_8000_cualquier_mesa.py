"""
Promoción corregida por el propietario (24 nov. 2026): la hora de billar en cualquier mesa
(carambola o pool) a $ 8.000, hasta las 3:00 p. m.

Reemplaza la promoción que creó la 0004 («tres bandas, a $ 7.500», lunes a viernes).
Si esa ya no existe (el club la borró o le cambió el título en el panel), crea la nueva
solo si no hay otra con el mismo título. Después se administra desde el panel.
"""
from django.db import migrations

TITULO_ANTERIOR = "La hora de billar a tres bandas, a $ 7.500"
TITULO = "La hora de billar en cualquier mesa, a $ 8.000"
DATOS = {
    "descripcion": "Carambola o pool, hasta las 3:00 p. m.",
    "enlace_url": "/reservas/",
    "enlace_texto": "Reservar mesa",
}


def actualizar(apps, schema_editor):
    Promocion = apps.get_model("club", "Promocion")
    if Promocion.objects.filter(titulo=TITULO_ANTERIOR).update(titulo=TITULO, **DATOS):
        return
    if not Promocion.objects.filter(titulo=TITULO).exists():
        Promocion.objects.create(titulo=TITULO, destacada=True, activa=True, orden=0, **DATOS)


class Migration(migrations.Migration):
    dependencies = [("club", "0005_inventario_de_mesas")]
    operations = [migrations.RunPython(actualizar, migrations.RunPython.noop)]
