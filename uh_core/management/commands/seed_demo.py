from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from uh_academico.models import (
    CalificacionDetalle,
    CicloEscolar,
    InscripcionPeriodo,
    Materia,
    PeriodoAcademico,
    PlanEstudio,
    TrayectoriaAcademica,
    TipoPeriodo,
)
from uh_auditoria.models import AuditoriaSistema
from uh_core.models import PlantelAutoridad
from uh_documentos.models import DocumentoEmitido, TipoDocumento
from uh_documentos.services import crear_documento


def _calificacion_letra(n: float) -> str:
    if n >= 95:
        return "MB"
    if n >= 85:
        return "B"
    if n >= 70:
        return "S"
    return "NA"


class Command(BaseCommand):
    help = "Genera datos ficticios para periodos, calificaciones, documentos emitidos y auditoría."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=1337)
        parser.add_argument("--docs", type=int, default=20)
        parser.add_argument("--periodos", type=int, default=4)
        parser.add_argument("--materias-por-periodo", type=int, default=6)

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(int(options["seed"]))
        docs_target = int(options["docs"])
        periodos_n = int(options["periodos"])
        materias_por_periodo = int(options["materias_por_periodo"])

        if TrayectoriaAcademica.objects.count() == 0:
            self.stdout.write(self.style.ERROR("No hay trayectorias académicas. Ejecuta primero importar_fixtures_csv."))
            return

        now = timezone.now()

        trayectorias = list(TrayectoriaAcademica.objects.select_related("carrera__plantel").all())

        created_insc = 0
        created_calif = 0

        for t in trayectorias:
            regimen = (getattr(t.carrera, "regimen", "") or "").strip().lower()
            tipo_nombre = "CUATRIMESTRAL" if "cuatri" in regimen else "SEMESTRAL"
            per_year = 3 if tipo_nombre == "CUATRIMESTRAL" else 2
            tipo_periodo_obj, _ = TipoPeriodo.objects.get_or_create(
                nombre=tipo_nombre,
                defaults={"duracion_meses": 4 if tipo_nombre == "CUATRIMESTRAL" else 6, "ciclos_por_anio": per_year},
            )
            if not getattr(t.carrera, "tipo_periodo_id", None):
                t.carrera.tipo_periodo = tipo_periodo_obj
                t.carrera.save(update_fields=["tipo_periodo"])

            plan = (
                PlanEstudio.objects.filter(carrera=t.carrera)
                .order_by("-version", "-id")
                .first()
            )
            if not plan:
                continue

            materias = list(Materia.objects.filter(plan_estudio=plan).order_by("ciclo_numero", "id"))
            if not materias:
                continue

            cycle_start_year = now.year - 1
            ciclo_actual, _ = CicloEscolar.objects.get_or_create(
                anio_inicio=cycle_start_year,
                anio_fin=cycle_start_year + 1,
                defaults={"clave": f"{cycle_start_year}-{cycle_start_year + 1}"},
            )

            periodos_creados = []
            for idx in range(periodos_n):
                year = cycle_start_year + (idx // per_year)
                term = (idx % per_year) + 1
                clave_periodo = f"{year}-{term}"
                fecha_inicio = date(year, 1, 1) + timedelta(days=(term - 1) * (365 // per_year))
                if term == per_year:
                    fecha_fin = date(year, 12, 31)
                else:
                    siguiente_anio = year if term < per_year else year + 1
                    fecha_fin = date(siguiente_anio, 1, 1) - timedelta(days=1)
                periodo_obj, _ = PeriodoAcademico.objects.get_or_create(
                    ciclo_escolar=ciclo_actual,
                    tipo_periodo=tipo_periodo_obj,
                    clave=clave_periodo,
                    numero=term,
                    defaults={"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
                )
                periodos_creados.append(periodo_obj)

            for idx, per_obj in enumerate(periodos_creados):
                insc, insc_created = InscripcionPeriodo.objects.get_or_create(
                    trayectoria_academica=t,
                    periodo_academico=per_obj,
                    defaults={
                        "estatus": InscripcionPeriodo.ESTATUS_CURSANDO,
                        "es_actual": idx == len(periodos_creados) - 1,
                    },
                )
                if insc_created:
                    created_insc += 1

                picks = materias[: materias_por_periodo] if len(materias) >= materias_por_periodo else materias
                for m in picks:
                    base = random.randint(60, 100)
                    final = float(base)
                    letra = _calificacion_letra(final)
                    _, created = CalificacionDetalle.objects.get_or_create(
                        inscripcion_periodo=insc,
                        catalogo_materia=m,
                        defaults={
                            "calificacion_ordinaria": float(base),
                            "calificacion_final": final,
                            "calificacion_letra": letra,
                        },
                    )
                    if created:
                        created_calif += 1

                prom = (
                    CalificacionDetalle.objects.filter(inscripcion_periodo=insc)
                    .exclude(calificacion_final__isnull=True)
                    .values_list("calificacion_final", flat=True)
                )
                vals = list(prom)
                if vals:
                    insc.promedio_periodo = float(sum(vals) / len(vals))
                    insc.save(update_fields=["promedio_periodo"])

        tipos = list(TipoDocumento.objects.all().order_by("id"))
        if not tipos:
            self.stdout.write(self.style.ERROR("No hay tipos de documento. Ejecuta primero importar_fixtures_csv."))
            return

        docs_exist = DocumentoEmitido.objects.count()
        docs_to_create = max(0, docs_target - docs_exist)

        created_docs = 0
        created_aud = 0
        if docs_to_create > 0:
            for t in trayectorias:
                if created_docs >= docs_to_create:
                    break

                plantel_id = t.carrera.plantel_id
                pa = PlantelAutoridad.objects.filter(plantel_id=plantel_id).select_related("autoridad").first()
                autoridad_id = pa.autoridad_id if pa else None
                doc = None
                shuffled = tipos[:]
                random.shuffle(shuffled)
                for tipo in shuffled:
                    try:
                        doc = crear_documento(
                            tipo_documento=tipo,
                            plantel_id=plantel_id,
                            autoridad_id=autoridad_id,
                            alumno_id=t.alumno_id,
                            externo_payload=None,
                            aprobado_directiva=True,
                            archivo=None,
                        )
                        break
                    except ValidationError:
                        continue

                if not doc:
                    continue

                created_docs += 1

                AuditoriaSistema.objects.create(
                    usuario=None,
                    accion="documento_emitido_creado",
                    modelo_afectado="documentos_emitidos",
                    registro_id=doc.id,
                    detalles_cambio={"folio": doc.folio, "tipo_documento_id": doc.tipo_documento_id},
                    ip_origen="127.0.0.1",
                    fecha_hora=now - timedelta(minutes=random.randint(0, 5000)),
                )
                created_aud += 1

        self.stdout.write(
            self.style.SUCCESS(
                "seed_demo OK | "
                f"periodos={PeriodoAcademico.objects.count()} "
                f"inscripciones+={created_insc} "
                f"calificaciones+={created_calif} "
                f"documentos+={created_docs} "
                f"auditoria+={created_aud}"
            )
        )
