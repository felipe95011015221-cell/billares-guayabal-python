#!/usr/bin/env bash
# Construcción en Render: dependencias, archivos estáticos, base de datos y datos iniciales.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py cargar_datos_iniciales   # sin --demo: nunca crea datos ficticios en producción

# Administrador inicial (solo si definiste estas variables en Render; si ya existe, no hace nada).
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --no-input || echo "El administrador ya existe."
fi
