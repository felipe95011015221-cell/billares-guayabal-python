"""
Dos mesas de pool más, en el segundo piso (pedido del propietario, 27 nov. 2026): «Mesa 8» y «Mesa 9»,
a COP 15.000 la hora. El inventario queda en 5 mesas de tres bandas y 4 de pool.

- Solo agrega las que falten por nombre; nunca borra ni modifica mesas existentes. Es idempotente.
- Si todavía no hay ninguna mesa, no hace nada: las crea «cargar_datos_iniciales» con el inventario completo.
"""
from django.db import migrations

TARIFA_HORA = 15000
NUEVAS = [("Mesa 8", "pool"), ("Mesa 9", "pool")]


def agregar(apps, schema_editor):
    Mesa = apps.get_model("club", "Mesa")
    if not Mesa.objects.exists():
        return
    orden = (Mesa.objects.order_by("-orden").values_list("orden", flat=True).first() or 0) + 1
    for nombre, modalidad in NUEVAS:
        if not Mesa.objects.filter(nombre=nombre).exists():
            Mesa.objects.create(nombre=nombre, modalidad=modalidad, orden=orden, tarifa_hora=TARIFA_HORA)
            orden += 1


class Migration(migrations.Migration):
    dependencies = [("club", "0006_promocion_8000_cualquier_mesa")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
