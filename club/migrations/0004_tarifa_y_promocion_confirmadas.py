"""
Datos confirmados por el propietario (23 nov. 2026), cargados UNA sola vez:

- Tarifa por hora de las mesas: COP 15.000. Solo se asigna a las mesas que no tienen tarifa,
  así que no pisa lo que el club ya haya editado en el panel.
- Inventario de mesas (confirmado): Mesa 1 a Mesa 5 de carambola a tres bandas; Mesa 6 y Mesa 7 de pool.
  * Si las mesas son las de ejemplo («Mesa 1»…«Mesa 6»), se deja exactamente ese esquema: se crea lo que falta y
    una mesa cuya modalidad no coincide se corrige SOLO si no tiene reservas ni bloqueos (nunca se reasigna una
    mesa con historial: eso lo decide el club en el panel).
  * Si el club ya les puso otros nombres, no se tocan: solo se agregan las que falten hasta 5 y 2.
  * Si todavía no hay ninguna mesa, no hace nada: las crea «cargar_datos_iniciales».
- Promoción «La hora de billar a tres bandas, a $ 7.500», antes de las 3 p. m. de lunes a viernes.
  Se crea si no existe una con ese título. Después se administra desde el panel (editar, desactivar o borrar):
  como es una migración, no se vuelve a crear en los siguientes despliegues.
"""
from django.db import migrations

TARIFA_HORA = 15000
MESAS_ESPERADAS = {"carambola": 5, "pool": 2}
ESQUEMA = [("Mesa 1", "carambola"), ("Mesa 2", "carambola"), ("Mesa 3", "carambola"), ("Mesa 4", "carambola"),
           ("Mesa 5", "carambola"), ("Mesa 6", "pool"), ("Mesa 7", "pool")]
TITULO_PROMOCION = "La hora de billar a tres bandas, a $ 7.500"


def cargar(apps, schema_editor):
    Mesa = apps.get_model("club", "Mesa")
    Promocion = apps.get_model("club", "Promocion")
    if Mesa.objects.exists():
        Reserva = apps.get_model("club", "Reserva")
        Bloqueo = apps.get_model("club", "Bloqueo")
        existentes = {m.nombre: m for m in Mesa.objects.all()}
        if set(existentes) <= {n for n, _ in ESQUEMA}:  # solo hay mesas con los nombres de ejemplo
            for orden, (nombre, modalidad) in enumerate(ESQUEMA, 1):
                mesa = existentes.get(nombre)
                if mesa is None:
                    Mesa.objects.create(nombre=nombre, modalidad=modalidad, orden=orden, tarifa_hora=TARIFA_HORA)
                elif mesa.modalidad != modalidad and not (
                    Reserva.objects.filter(mesa=mesa).exists() or Bloqueo.objects.filter(mesa=mesa).exists()
                ):
                    mesa.modalidad = modalidad
                    mesa.orden = orden
                    mesa.save(update_fields=["modalidad", "orden"])
        else:  # nombres propios del club: solo completar la cantidad, sin tocar ninguna mesa
            nombres = set(existentes)
            orden = (Mesa.objects.order_by("-orden").values_list("orden", flat=True).first() or 0) + 1
            numero = 1
            for modalidad, esperadas in MESAS_ESPERADAS.items():
                for _ in range(esperadas - Mesa.objects.filter(modalidad=modalidad).count()):
                    while f"Mesa {numero}" in nombres:
                        numero += 1
                    nombres.add(f"Mesa {numero}")
                    Mesa.objects.create(nombre=f"Mesa {numero}", modalidad=modalidad, orden=orden, tarifa_hora=TARIFA_HORA)
                    orden += 1
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
