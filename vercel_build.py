"""Paso de construcción en Vercel: migraciones, tabla de caché, datos iniciales y administrador.

Usa la conexión directa de Neon (DATABASE_URL_UNPOOLED) para las migraciones si existe.
"""
import os
import subprocess
import sys

entorno = dict(os.environ)
if entorno.get("DATABASE_URL_UNPOOLED"):
    entorno["DATABASE_URL"] = entorno["DATABASE_URL_UNPOOLED"]

if not (entorno.get("DATABASE_URL") or entorno.get("POSTGRES_URL")):
    print("Sin DATABASE_URL: se omite la preparación de la base de datos.")
    sys.exit(0)


def manage(*args, obligatorio=True):
    print("$ manage.py", *args, flush=True)
    r = subprocess.run([sys.executable, "manage.py", *args], env=entorno)
    if r.returncode and obligatorio:
        sys.exit(r.returncode)


manage("migrate", "--no-input")
manage("createcachetable")
manage("cargar_datos_iniciales")  # nunca con --demo en producción
if entorno.get("DJANGO_SUPERUSER_USERNAME") and entorno.get("DJANGO_SUPERUSER_PASSWORD"):
    manage("createsuperuser", "--no-input", obligatorio=False)  # si ya existe, no falla el despliegue
