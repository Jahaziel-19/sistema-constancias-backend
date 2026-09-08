import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from uh_documentos.models import TipoDocumento

tipo, _ = TipoDocumento.objects.get_or_create(
    nombre="Constancia de Estudios",
    defaults={
        "descripcion": "Constancia oficial de estudios para alumnos activos",
        "aplica_a": "alumno",
        "categoria": TipoDocumento.CONSTANCIAS,
        "plantilla": "constancia_estudios.html",
        "reglas_validacion": {},
    },
)

print(f"TipoDocumento listo: {tipo.nombre} -> {tipo.plantilla}")
