import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from uh_academico.models import Alumno, Materia, PeriodoAcademico, PlanEstudio, TrayectoriaAcademica, TipoPeriodo
from uh_core.models import (
    Autoridad,
    Carrera,
    DatosContacto,
    Domicilio,
    EstatusAcademico,
    Plantel,
    PlantelAutoridad,
)
from uh_documentos.models import TipoDocumento


class Command(BaseCommand):
    help = "Importa fixtures CSV desde Informacion Tecnica/fixtures"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="",
            help="Ruta a la carpeta fixtures (por defecto: ../Informacion Tecnica/fixtures)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[4]
        default_path = base_dir / "Informacion Tecnica" / "fixtures"
        fixtures_path = Path(options["path"]).resolve() if options["path"] else default_path

        if not fixtures_path.exists():
            raise FileNotFoundError(f"No existe la carpeta fixtures: {fixtures_path}")

        self._importar_estatus(fixtures_path / "estatus_academicos.csv")
        self._importar_planteles(fixtures_path / "planteles.csv")
        self._importar_carreras(fixtures_path / "carreras.csv")
        self._importar_planes(fixtures_path / "planes_estudio.csv")
        self._importar_materias(fixtures_path / "materias.csv")
        self._importar_alumnos(fixtures_path / "alumnos.csv")
        self._importar_autoridades(fixtures_path / "autoridades.csv")
        self._importar_tipos_documento(fixtures_path / "tipos_de_documento.csv")

        self.stdout.write(self.style.SUCCESS("Fixtures importados correctamente."))

    def _reader(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            first_line = f.readline()
            f.seek(0)
            if first_line.startswith("#"):
                while True:
                    pos = f.tell()
                    line = f.readline()
                    if not line:
                        break
                    if not line.startswith("#"):
                        f.seek(pos)
                        break
            yield from csv.DictReader(f)

    def _importar_estatus(self, path: Path):
        for row in self._reader(path):
            EstatusAcademico.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "nombre": row["nombre"],
                    "descripcion": row.get("descripcion", "") or "",
                },
            )

    def _importar_planteles(self, path: Path):
        for row in self._reader(path):
            domicilio = Domicilio.objects.create(
                calle=row.get("domicilio_calle", "") or "",
                colonia=row.get("domicilio_colonia", "") or "",
                municipio=row.get("domicilio_municipio", "") or "",
                estado=row.get("domicilio_estado", "") or "",
            )
            contacto = DatosContacto.objects.create(
                telefono=row.get("contacto_telefono", "") or "",
                correo_electronico=row.get("contacto_correo", "") or "",
            )
            municipio = row.get("domicilio_municipio", "") or ""
            Plantel.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "clave_plantel": row.get("clave_institucion", "") or row.get("clave_cct", "") or f"PL-{row['id']}",
                    "nombre": f"Plantel {municipio}".strip(),
                    "rgp": row.get("registro_general_profesiones", "") or "",
                    "pagina_web": row.get("pagina_web", "") or "",
                    "domicilio": domicilio,
                    "contacto": contacto,
                },
            )

    def _importar_carreras(self, path: Path):
        for row in self._reader(path):
            regimen = (row.get("regimen", "") or "").strip().lower()
            tipo_nombre = "CUATRIMESTRAL" if "cuatri" in regimen else "SEMESTRAL"
            tipo_periodo_obj, _ = TipoPeriodo.objects.get_or_create(
                nombre=tipo_nombre,
                defaults={"duracion_meses": 4 if tipo_nombre == "CUATRIMESTRAL" else 6, "ciclos_por_anio": 3 if tipo_nombre == "CUATRIMESTRAL" else 2},
            )
            Carrera.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "plantel_id": int(row["plantel_id"]),
                    "nombre": row["nombre"],
                    "regimen": row.get("regimen", "") or "",
                    "tipo_periodo": tipo_periodo_obj,
                    "total_ciclos": int(row.get("total_ciclos") or 0) or None,
                    "acuerdo_sep": row.get("acuerdo_sep", "") or "",
                    "fecha_acuerdo_sep": row.get("fecha_acuerdo_sep") or None,
                },
            )

    def _importar_planes(self, path: Path):
        for row in self._reader(path):
            PlanEstudio.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "carrera_id": int(row["carrera_id"]),
                    "clave_plan": row["clave_plan"],
                    "version": int(row.get("version") or 1),
                    "creditos_totales": int(row.get("creditos_totales") or 0) or None,
                    "vigencia_inicio": row.get("vigencia_inicio") or None,
                },
            )

    def _importar_materias(self, path: Path):
        for row in self._reader(path):
            Materia.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "plan_estudio_id": int(row["plan_estudio_id"]),
                    "ciclo_numero": int(row["ciclo_numero"]),
                    "clave_materia": row["clave_materia"],
                    "nombre_materia": row["nombre_materia"],
                    "creditos": int(row.get("creditos") or 0) or None,
                },
            )

    def _importar_alumnos(self, path: Path):
        for row in self._reader(path):
            domicilio = Domicilio.objects.create(
                calle=row.get("calle", "") or "",
                colonia=row.get("colonia", "") or "",
                municipio=row.get("municipio", "") or "",
                estado=row.get("estado", "") or "",
            )
            contacto = DatosContacto.objects.create(
                telefono=row.get("telefono", "") or "",
                correo_electronico=row.get("correo", "") or "",
            )
            alumno, _ = Alumno.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "matricula": row["matricula"],
                    "nombres": row["nombres"],
                    "primer_apellido": row["primer_apellido"],
                    "segundo_apellido": row.get("segundo_apellido", "") or "",
                    "curp": row["curp"],
                    "fecha_nacimiento": row.get("fecha_nacimiento") or None,
                    "genero": row.get("genero", "") or "",
                    "domicilio": domicilio,
                    "contacto": contacto,
                },
            )
            TrayectoriaAcademica.objects.filter(alumno=alumno).update(es_actual=False)
            nivel_raw = row.get("nivel_actual", "") or ""
            try:
                nivel_int = int("".join(filter(str.isdigit, str(nivel_raw))))
            except Exception:
                nivel_int = None
            TrayectoriaAcademica.objects.update_or_create(
                alumno=alumno,
                carrera_id=int(row["carrera_id"]),
                defaults={
                    "estatus_academico_id": int(row["estatus_academico_id"]),
                    "nivel_actual": nivel_int,
                    "es_actual": True,
                },
            )

    def _importar_autoridades(self, path: Path):
        for row in self._reader(path):
            apellidos = " ".join([row.get("primer_apellido", "") or "", row.get("segundo_apellido", "") or ""]).strip()
            autoridad, _ = Autoridad.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "nombres": row["nombres"],
                    "apellidos": apellidos,
                    "cargo": row.get("cargo", "") or "",
                    "curp": row.get("curp_autoridad", "") or "",
                },
            )
            PlantelAutoridad.objects.update_or_create(
                plantel_id=int(row["plantel_id"]),
                autoridad=autoridad,
            )

    def _importar_tipos_documento(self, path: Path):
        for row in self._reader(path):
            reglas_raw = row.get("reglas_validacion", "") or "{}"
            reglas = json.loads(reglas_raw)
            TipoDocumento.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "nombre": row["nombre"],
                    "descripcion": row.get("descripcion", "") or "",
                    "aplica_a": row.get("aplica_a", "") or "",
                    "categoria": row.get("categoria", "") or "CONSTANCIAS",
                    "reglas_validacion": reglas,
                },
            )
