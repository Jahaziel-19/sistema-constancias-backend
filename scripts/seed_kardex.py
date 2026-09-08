import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from decimal import Decimal
from datetime import date, timedelta

from uh_academico.models import (
    Alumno,
    CalificacionDetalle,
    CicloEscolar,
    InscripcionPeriodo,
    Materia,
    PeriodoAcademico,
    PlanEstudio,
    TrayectoriaAcademica,
    TipoPeriodo,
)
from uh_core.models import Autoridad, Carrera, DatosContacto, Domicilio, EstatusAcademico, Plantel
from uh_documentos.models import TipoDocumento

# Ensure base catalogs exist
tipo_periodo, _ = TipoPeriodo.objects.get_or_create(
    nombre="Semestral",
    defaults={"duracion_meses": 6, "ciclos_por_anio": 2},
)
estatus, _ = EstatusAcademico.objects.get_or_create(
    nombre="Activo",
    defaults={"descripcion": "Estatus activo para alumno de prueba"},
)

# Plantel
dom_plantel, _ = Domicilio.objects.get_or_create(
    calle="Av. Principal", numero_exterior="123", colonia="Centro", codigo_postal="12345", municipio="Guadalajara", estado="Jalisco"
)
contacto_plantel, _ = DatosContacto.objects.get_or_create(
    correo_electronico="plantel@hispana.edu.mx", defaults={"telefono": "33-1234-5678", "celular": "33-9876-5432"}
)
plantel, _ = Plantel.objects.get_or_create(
    clave_plantel="GDL",
    defaults={
        "nombre": "Plantel Guadalajara",
        "rgp": "RGP-001",
        "pagina_web": "https://hispana.edu.mx",
        "domicilio": dom_plantel,
        "contacto": contacto_plantel,
    },
)

# Carrera y plan
carrera, _ = Carrera.objects.get_or_create(
    nombre="Psicología",
    plantel=plantel,
    defaults={"regimen": "Escolarizado", "tipo_periodo": tipo_periodo, "total_ciclos": 9, "acuerdo_sep": "ACUERDO-PSI-001"},
)
plan, _ = PlanEstudio.objects.get_or_create(
    carrera=carrera,
    clave_plan="PSI-2024",
    version=1,
    defaults={"creditos_totales": 320, "vigencia_inicio": date(2024, 1, 1)},
)

# Alumno
dom_alumno, _ = Domicilio.objects.get_or_create(
    calle="Callejon", numero_exterior="456", colonia="Americana", codigo_postal="44100", municipio="Guadalajara", estado="Jalisco"
)
contacto_alumno, _ = DatosContacto.objects.get_or_create(
    correo_electronico="alumno.prueba@hispana.edu.mx", defaults={"telefono": "33-1111-2222", "celular": "33-3333-4444"}
)
alumno, _ = Alumno.objects.get_or_create(
    matricula="2024PSI001",
    defaults={
        "nombres": "Ana",
        "primer_apellido": "López",
        "segundo_apellido": "García",
        "curp": "LOGA950123MDFRRN09",
        "domicilio": dom_alumno,
        "contacto": contacto_alumno,
    },
)

# Trayectoria
trayectoria, _ = TrayectoriaAcademica.objects.get_or_create(
    alumno=alumno,
    carrera=carrera,
    estatus_academico=estatus,
    defaults={"promedio_general": Decimal("8.50"), "creditos_acumulados": Decimal("180.00"), "nivel_actual": 6, "es_actual": True},
)

# Ciclos escolares (2-year cycles)
ciclo1, _ = CicloEscolar.objects.get_or_create(
    anio_inicio=2024, anio_fin=2025, defaults={"clave": "2024-2025"}
)
ciclo2, _ = CicloEscolar.objects.get_or_create(
    anio_inicio=2025, anio_fin=2026, defaults={"clave": "2025-2026"}
)

# Periodos academicos dentro de los ciclos
periodo1, _ = PeriodoAcademico.objects.get_or_create(
    ciclo_escolar=ciclo1,
    tipo_periodo=tipo_periodo,
    clave="2024-1",
    numero=1,
    defaults={"fecha_inicio": date(2024, 1, 1), "fecha_fin": date(2024, 6, 30)},
)
periodo2, _ = PeriodoAcademico.objects.get_or_create(
    ciclo_escolar=ciclo1,
    tipo_periodo=tipo_periodo,
    clave="2024-2",
    numero=2,
    defaults={"fecha_inicio": date(2024, 7, 1), "fecha_fin": date(2024, 12, 31)},
)
periodo3, _ = PeriodoAcademico.objects.get_or_create(
    ciclo_escolar=ciclo2,
    tipo_periodo=tipo_periodo,
    clave="2025-1",
    numero=1,
    defaults={"fecha_inicio": date(2025, 1, 1), "fecha_fin": date(2025, 6, 30)},
)
periodo4, _ = PeriodoAcademico.objects.get_or_create(
    ciclo_escolar=ciclo2,
    tipo_periodo=tipo_periodo,
    clave="2025-2",
    numero=2,
    defaults={"fecha_inicio": date(2025, 7, 1), "fecha_fin": date(2025, 12, 31)},
)

# Limpiar datos previos del plan
CalificacionDetalle.objects.filter(
    inscripcion_periodo__trayectoria_academica__alumno=alumno,
    catalogo_materia__plan_estudio=plan,
).delete()
InscripcionPeriodo.objects.filter(
    trayectoria_academica__alumno=alumno,
).delete()
Materia.objects.filter(plan_estudio=plan).delete()

# Materias del plan (9 ciclos, 6 materias por ciclo = 54)
materias = []
for ciclo in range(1, 10):
    for j in range(1, 7):
        clave = f"PSI-{ciclo:02d}-{j:02d}"
        nombre = f"Materia {ciclo}.{j}"
        mat, _ = Materia.objects.get_or_create(
            plan_estudio=plan,
            clave_materia=clave,
            defaults={"ciclo_numero": ciclo, "nombre_materia": nombre, "creditos": 5},
        )
        materias.append(mat)

# Calificar 50% de las materias (27 de 54)
from random import Random
rng = Random(42)
calificar_ids = set(rng.sample([m.id for m in materias], 27))
calificadas = set()
for idx, mat in enumerate(materias):
    if mat.id not in calificar_ids:
        continue
    per = periodo1 if mat.ciclo_numero <= 3 else (periodo2 if mat.ciclo_numero <= 6 else periodo3)
    insc, _ = InscripcionPeriodo.objects.get_or_create(
        trayectoria_academica=trayectoria,
        periodo_academico=per,
        defaults={"promedio_periodo": Decimal("8.00"), "estatus": "CURSANDO", "es_actual": True},
    )
    CalificacionDetalle.objects.get_or_create(
        inscripcion_periodo=insc,
        catalogo_materia=mat,
        defaults={
            "calificacion_ordinaria": Decimal("8.00"),
            "extraordinario_1": None,
            "extraordinario_2": None,
            "calificacion_final": Decimal("8.00"),
            "calificacion_letra": "OCHO",
        },
    )
    calificadas.add(mat.id)

# TipoDocumento Kardex
tipo_kardex, _ = TipoDocumento.objects.get_or_create(
    nombre="Kardex de alumno",
    defaults={
        "descripcion": "Kardex académico oficial",
        "aplica_a": "alumno",
        "categoria": TipoDocumento.KARDEX,
        "plantilla": "kardex.html",
        "reglas_validacion": {},
    },
)

print("Seed completado:")
print(f"- Plantel: {plantel.nombre}")
print(f"- Carrera: {carrera.nombre}")
print(f"- Plan: {plan.clave_plan} ({Materia.objects.filter(plan_estudio=plan).count()} materias)")
print(f"- Alumno: {alumno.matricula} - {alumno.nombres} {alumno.primer_apellido}")
print(f"- Trayectoria: {trayectoria.carrera.nombre} ({trayectoria.estatus_academico.nombre})")
print(f"- Calificaciones creadas: {CalificacionDetalle.objects.filter(inscripcion_periodo__trayectoria_academica__alumno=alumno).count()}")
print(f"- TipoDocumento Kardex: {tipo_kardex.nombre} -> {tipo_kardex.plantilla}")
