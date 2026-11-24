"""
Garantía anti-doble reserva a nivel de base de datos (solo PostgreSQL):
dos reservas activas no pueden solaparse en la misma mesa, aunque lleguen al mismo tiempo.
En SQLite (desarrollo) la protección la da la transacción IMMEDIATE + la re-verificación en servicios.py.
"""
from django.db import migrations

SQL_CREAR = [
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    """ALTER TABLE club_reserva ADD CONSTRAINT reservas_sin_solapamiento
  EXCLUDE USING gist (mesa_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)
  WHERE (estado IN ('pendiente', 'confirmada', 'en_curso'))""",
]
SQL_BORRAR = "ALTER TABLE club_reserva DROP CONSTRAINT IF EXISTS reservas_sin_solapamiento;"


def crear(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        for sql in SQL_CREAR:  # una sentencia por llamada (psycopg 3)
            schema_editor.execute(sql)


def borrar(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL_BORRAR)


class Migration(migrations.Migration):
    dependencies = [("club", "0001_initial")]
    operations = [migrations.RunPython(crear, borrar)]
