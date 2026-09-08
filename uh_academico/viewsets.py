from datetime import datetime
import base64
import os
from pathlib import Path
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

from django.conf import settings

from uh_academico.models import (
    Alumno,
    CalificacionDetalle,
    Carrera,
    CicloEscolar,
    DatosContacto,
    Domicilio,
    EstatusAcademico,
    InscripcionPeriodo,
    Materia,
    PeriodoAcademico,
    PlanEstudio,
    TrayectoriaAcademica,
    TipoPeriodo,
)
from uh_academico.serializers import (
    AlumnoSerializer,
    CalificacionDetalleSerializer,
    CicloEscolarSerializer,
    InscripcionPeriodoSerializer,
    MateriaSerializer,
    PeriodoAcademicoSerializer,
    PlanEstudioSerializer,
    TrayectoriaAcademicaSerializer,
    TipoPeriodoSerializer,
)
from uh_usuarios.access import es_admin, planteles_usuario


def _carrera_en_planteles(user, carrera_id, planteles):
    if es_admin(user):
        return True
    if not planteles:
        return True
    return Carrera.objects.filter(pk=carrera_id, plantel_id__in=planteles).exists()


class AlumnoViewSet(viewsets.ModelViewSet):
    queryset = Alumno.objects.all().order_by("id")
    serializer_class = AlumnoSerializer
    parser_classes = [MultiPartParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        if es_admin(self.request.user):
            return qs
        planteles = planteles_usuario(self.request.user)
        if planteles:
            qs = qs.filter(
                trayectorias__es_actual=True,
                trayectorias__carrera__plantel_id__in=planteles,
            ).distinct()
        return qs

    @action(detail=True, methods=["get"], url_path="kardex")
    def kardex(self, request, pk=None):
        alumno = self.get_object()
        trayectoria = (
            alumno.trayectorias.filter(es_actual=True)
            .select_related("carrera__plantel", "estatus_academico")
            .first()
        )
        plan = None
        materias = []
        if trayectoria and trayectoria.carrera_id:
            plan = (
                PlanEstudio.objects
                .filter(carrera_id=trayectoria.carrera_id)
                .order_by("-vigencia_inicio", "-version", "-id")
                .first()
            )
            if plan:
                materias = list(
                    Materia.objects
                    .filter(plan_estudio_id=plan.id)
                    .order_by("ciclo_numero", "clave_materia")
                )
        califs = []
        if materias:
            califs = list(
                CalificacionDetalle.objects
                .filter(
                    inscripcion_periodo__trayectoria_academica__alumno=alumno,
                    catalogo_materia__plan_estudio_id=plan.id,
                )
                .select_related(
                    "inscripcion_periodo",
                    "inscripcion_periodo__periodo_academico",
                    "inscripcion_periodo__periodo_academico__ciclo_escolar",
                    "catalogo_materia",
                )
                .order_by(
                    "inscripcion_periodo__periodo_academico__ciclo_escolar__anio_inicio",
                    "inscripcion_periodo__periodo_academico__numero",
                    "catalogo_materia__ciclo_numero",
                )
            )
        calif_por_materia = {}
        for det in califs:
            mat = det.catalogo_materia
            calif_por_materia[mat.id] = {
                "inscripcion_periodo_id": det.inscripcion_periodo_id,
                "calificacion_ordinaria": det.calificacion_ordinaria,
                "extraordinario_1": det.extraordinario_1,
                "extraordinario_2": det.extraordinario_2,
                "calificacion_final": det.calificacion_final,
                "calificacion_letra": det.calificacion_letra,
            }
        materias_items = []
        last_ciclo = None
        for mat in materias:
            c = calif_por_materia.get(mat.id)
            ciclo = mat.ciclo_numero
            if ciclo != last_ciclo:
                materias_items.append({
                    "_periodo_separador": True,
                    "_periodo_label": f"{ciclo}° ciclo",
                })
                last_ciclo = ciclo
            materias_items.append({
                "_periodo_separador": False,
                "materia_id": mat.id,
                "ciclo_numero": mat.ciclo_numero,
                "clave_materia": mat.clave_materia,
                "nombre_materia": mat.nombre_materia,
                "creditos": mat.creditos,
                "calificacion_ordinaria": c["calificacion_ordinaria"] if c else None,
                "extraordinario_1": c["extraordinario_1"] if c else None,
                "extraordinario_2": c["extraordinario_2"] if c else None,
                "calificacion_final": c["calificacion_final"] if c else None,
                "calificacion_letra": c["calificacion_letra"] if c else "",
            })
        data = {
            "alumno": AlumnoSerializer(alumno).data,
            "trayectoria": TrayectoriaAcademicaSerializer(trayectoria).data if trayectoria else None,
            "plan": PlanEstudioSerializer(plan).data if plan else None,
            "materias": materias_items,
            "nivel_actual": trayectoria.nivel_actual if trayectoria else "",
            "tipo_periodo": {
                "id": trayectoria.carrera.tipo_periodo_id if trayectoria and trayectoria.carrera_id else None,
                "nombre": trayectoria.carrera.tipo_periodo.nombre if trayectoria and trayectoria.carrera.tipo_periodo else "",
            } if trayectoria and trayectoria.carrera_id else None,
        }
        return Response(data)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response({"detail": "items debe ser una lista."}, status=400)

        created = []
        updated = []
        skipped = []
        errors = []

        for idx, item in enumerate(items):
            row_num = idx + 2
            try:
                matricula = str(item.get("matricula", "")).strip()
                if not matricula:
                    errors.append({"row": row_num, "matricula": matricula, "message": "La matrícula es requerida."})
                    continue

                nombre = str(item.get("nombre", "")).strip()
                primer_apellido = str(item.get("primer_apellido", "")).strip()
                segundo_apellido = str(item.get("segundo_apellido", "")).strip()
                curp = str(item.get("curp", "")).strip()

                if not nombre or not primer_apellido or not curp:
                    errors.append({"row": row_num, "matricula": matricula, "message": "Faltan campos requeridos (nombre, primer_apellido, curp)."})
                    continue

                if len(curp) != 18:
                    errors.append({"row": row_num, "matricula": matricula, "message": f"CURP debe tener 18 caracteres (tiene {len(curp)})."})
                    continue

                fecha_nacimiento = None
                raw_fecha = str(item.get("fecha_nacimiento", "")).strip()
                if raw_fecha:
                    try:
                        fecha_nacimiento = datetime.strptime(raw_fecha, "%d/%m/%Y").date()
                    except Exception:
                        errors.append({"row": row_num, "matricula": matricula, "message": f"Formato de fecha inválido: {raw_fecha}. Use dd/mm/aaaa."})
                        continue

                genero = str(item.get("genero", "")).strip().upper()
                if genero and genero not in ("M", "F"):
                    errors.append({"row": row_num, "matricula": matricula, "message": f"Género inválido: {genero}. Use M o F."})
                    continue

                alumno = Alumno.objects.filter(matricula=matricula).first()
                domicilio = alumno.domicilio if alumno and alumno.domicilio_id else None
                contacto = alumno.contacto if alumno and alumno.contacto_id else None

                foto_value = str(item.get("foto", "")).strip()
                if foto_value:
                    processed = _procesar_foto_bulk(foto_value, matricula)
                    if processed:
                        item_foto = processed
                    else:
                        item_foto = alumno.foto if alumno and alumno.foto else ""
                        errors.append({
                            "row": row_num,
                            "matricula": matricula,
                            "message": f"No se pudo leer la foto desde la ruta: {foto_value}. Se conservó la foto anterior o se dejó vacía.",
                        })
                else:
                    item_foto = alumno.foto if alumno else ""

                alumno_incoming = {
                    "nombres": nombre,
                    "primer_apellido": primer_apellido,
                    "segundo_apellido": segundo_apellido,
                    "curp": curp,
                    "fecha_nacimiento": fecha_nacimiento,
                    "genero": genero,
                    "foto": item_foto,
                }

                domicilio_incoming = {
                    "calle": str(item.get("calle", "")).strip(),
                    "numero_exterior": str(item.get("numero_exterior", "")).strip(),
                    "numero_interior": str(item.get("numero_interior", "")).strip(),
                    "colonia": str(item.get("colonia", "")).strip(),
                    "codigo_postal": str(item.get("codigo_postal", "")).strip(),
                    "municipio": str(item.get("municipio", "")).strip(),
                    "estado": str(item.get("estado", "")).strip(),
                }

                contacto_incoming = {
                    "telefono": str(item.get("telefono", "")).strip(),
                    "celular": str(item.get("celular", "")).strip(),
                    "correo_electronico": str(item.get("correo_electronico", "")).strip(),
                }

                if alumno and _is_equal_alumno(alumno, alumno_incoming) and _is_equal_domicilio(domicilio, domicilio_incoming) and _is_equal_contacto(contacto, contacto_incoming):
                    skipped.append({"row": row_num, "matricula": matricula, "alumno_id": alumno.id})
                    continue

                if not domicilio and any(v for v in domicilio_incoming.values()):
                    domicilio = Domicilio.objects.create(**domicilio_incoming)
                elif domicilio:
                    changed_d = False
                    for k, v in domicilio_incoming.items():
                        if getattr(domicilio, k) != v:
                            setattr(domicilio, k, v)
                            changed_d = True
                    if changed_d:
                        domicilio.save()

                if not contacto and any(v for v in contacto_incoming.values()):
                    contacto = DatosContacto.objects.create(**contacto_incoming)
                elif contacto:
                    changed_c = False
                    for k, v in contacto_incoming.items():
                        if getattr(contacto, k) != v:
                            setattr(contacto, k, v)
                            changed_c = True
                    if changed_c:
                        contacto.save()

                alumno_defaults = dict(alumno_incoming)
                if domicilio:
                    alumno_defaults["domicilio"] = domicilio
                if contacto:
                    alumno_defaults["contacto"] = contacto

                alumno, created_alumno = Alumno.objects.update_or_create(
                    matricula=matricula,
                    defaults=alumno_defaults,
                )

                (created if created_alumno else updated).append({"matricula": matricula, "alumno_id": alumno.id})

                carrera_nombre = str(item.get("carrera", "")).strip()
                estatus_nombre = str(item.get("estatus_academico", "")).strip()
                if carrera_nombre and estatus_nombre:
                    try:
                        carrera = Carrera.objects.get(nombre__iexact=carrera_nombre)
                    except Carrera.DoesNotExist:
                        errors.append({"row": row_num, "matricula": matricula, "message": f"Carrera no encontrada: {carrera_nombre}"})
                        continue
                    try:
                        estatus = EstatusAcademico.objects.get(nombre__iexact=estatus_nombre)
                    except EstatusAcademico.DoesNotExist:
                        errors.append({"row": row_num, "matricula": matricula, "message": f"Estatus académico no encontrado: {estatus_nombre}"})
                        continue

                    trayectoria_defaults = {
                        "carrera": carrera,
                        "estatus_academico": estatus,
                    }
                    nivel_actual = item.get("nivel_actual")
                    if nivel_actual not in (None, ""):
                        trayectoria_defaults["nivel_actual"] = int(nivel_actual)

                    promedio = item.get("promedio_general")
                    if promedio not in (None, ""):
                        trayectoria_defaults["promedio_general"] = float(promedio)

                    creditos = item.get("creditos_acumulados")
                    if creditos not in (None, ""):
                        trayectoria_defaults["creditos_acumulados"] = float(creditos)

                    titulacion = str(item.get("titulacion_en_proceso", "")).strip().lower()
                    if titulacion:
                        trayectoria_defaults["titulacion_en_proceso"] = titulacion in ("si", "sí", "true", "1", "yes")

                    es_actual = str(item.get("es_actual", "")).strip().lower()
                    if es_actual:
                        trayectoria_defaults["es_actual"] = es_actual in ("si", "sí", "true", "1", "yes")

                    TrayectoriaAcademica.objects.update_or_create(
                        alumno=alumno,
                        es_actual=trayectoria_defaults.get("es_actual", True),
                        defaults=trayectoria_defaults,
                    )

                (created if created_alumno else updated).append({"matricula": matricula, "alumno_id": alumno.id})
            except Exception as e:
                errors.append({"row": row_num, "matricula": item.get("matricula", ""), "message": str(e)})

        return Response({"created": created, "updated": updated, "skipped": skipped, "errors": errors})


class TrayectoriaAcademicaViewSet(viewsets.ModelViewSet):
    queryset = TrayectoriaAcademica.objects.all().order_by("id")
    serializer_class = TrayectoriaAcademicaSerializer


class TipoPeriodoViewSet(viewsets.ModelViewSet):
    queryset = TipoPeriodo.objects.all().order_by("id")
    serializer_class = TipoPeriodoSerializer


class PeriodoAcademicoViewSet(viewsets.ModelViewSet):
    queryset = PeriodoAcademico.objects.all().order_by("id")
    serializer_class = PeriodoAcademicoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        ciclo_escolar_id = self.request.query_params.get("ciclo_escolar_id")
        tipo_periodo_id = self.request.query_params.get("tipo_periodo_id")
        if ciclo_escolar_id and ciclo_escolar_id.isdigit():
            qs = qs.filter(ciclo_escolar_id=int(ciclo_escolar_id))
        if tipo_periodo_id and tipo_periodo_id.isdigit():
            qs = qs.filter(tipo_periodo_id=int(tipo_periodo_id))
        return qs


class CicloEscolarViewSet(viewsets.ModelViewSet):
    queryset = CicloEscolar.objects.all().order_by("anio_inicio", "anio_fin", "id")
    serializer_class = CicloEscolarSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tipo_periodo_id = self.request.query_params.get("tipo_periodo_id")
        anio_inicio = self.request.query_params.get("anio_inicio")
        if tipo_periodo_id and tipo_periodo_id.isdigit():
            qs = qs.filter(periodos__tipo_periodo_id=int(tipo_periodo_id)).distinct()
        if anio_inicio and anio_inicio.isdigit():
            qs = qs.filter(anio_inicio=int(anio_inicio))
        return qs

    @action(detail=False, methods=["get"], url_path="panel")
    def panel(self, request):
        rango = int(request.query_params.get("rango", 5))
        anio_actual = datetime.now().year
        anio_filtro = request.query_params.get("anio")
        ciclos_qs = CicloEscolar.objects.all().order_by("anio_inicio", "anio_fin", "id")
        if anio_filtro and anio_filtro.isdigit():
            anio_n = int(anio_filtro)
            ciclos_qs = ciclos_qs.filter(anio_inicio__lte=anio_n, anio_fin__gte=anio_n)
        ciclos = CicloEscolarSerializer(ciclos_qs, many=True).data
        existentes = set(
            CicloEscolar.objects.filter(anio_inicio__isnull=False, anio_fin__isnull=False)
            .values_list("anio_inicio", "anio_fin")
        )
        tipos = list(TipoPeriodo.objects.all())
        tipos_data = [{"id": t.id, "nombre": t.nombre} for t in tipos]
        sugerencias = []
        faltantes = []
        for offset in range(-rango, rango + 1):
            inicio = anio_actual + offset - 1
            fin = inicio + 1
            clave = f"{inicio}-{fin}"
            existe = (inicio, fin) in existentes
            sugerencias.append({"anio_inicio": inicio, "anio_fin": fin, "clave": clave, "existe": existe})
            if not existe:
                faltantes.append({"anio_inicio": inicio, "anio_fin": fin, "clave": clave})
        periodos_por_ciclo = {}
        for ciclo in ciclos_qs:
            periodos = list(
                PeriodoAcademico.objects.filter(ciclo_escolar=ciclo)
                .select_related("tipo_periodo")
                .order_by("tipo_periodo__nombre", "numero")
            )
            periodos_por_ciclo[ciclo.id] = [
                {
                    "id": p.id,
                    "ciclo_escolar": p.ciclo_escolar_id,
                    "tipo_periodo": p.tipo_periodo_id,
                    "tipo_periodo_nombre": getattr(getattr(p, "tipo_periodo", None), "nombre", ""),
                    "clave": p.clave,
                    "numero": p.numero,
                    "fecha_inicio": p.fecha_inicio,
                    "fecha_fin": p.fecha_fin,
                }
                for p in periodos
            ]
        return Response({
            "anio_actual": anio_actual,
            "rango": rango,
            "anio_filtro": anio_filtro if anio_filtro and anio_filtro.isdigit() else anio_actual,
            "ciclos": ciclos,
            "tipos_periodo": tipos_data,
            "sugerencias": sugerencias,
            "faltantes": faltantes,
            "total_faltantes": len(faltantes),
            "mostrar_sugerencia": len(faltantes) > 0,
            "periodos_por_ciclo": periodos_por_ciclo,
        })

    @action(detail=False, methods=["get"], url_path="sugerencias")
    def sugerencias(self, request):
        rango = int(request.query_params.get("rango", 5))
        anio_actual = datetime.now().year
        existentes = set(
            CicloEscolar.objects.filter(anio_inicio__isnull=False, anio_fin__isnull=False)
            .values_list("anio_inicio", "anio_fin")
        )
        sugerencias = []
        for offset in range(-rango, rango + 1):
            inicio = anio_actual + offset - 1
            fin = inicio + 1
            sugerencias.append({
                "anio_inicio": inicio,
                "anio_fin": fin,
                "clave": f"{inicio}-{fin}",
                "existe": (inicio, fin) in existentes,
            })
        faltantes = [s for s in sugerencias if not s["existe"]]
        return Response({
            "anio_actual": anio_actual,
            "rango": rango,
            "sugerencias": sugerencias,
            "faltantes": faltantes,
            "total_faltantes": len(faltantes),
        })

    @action(detail=False, methods=["post"], url_path="generar-automaticos")
    def generar_automaticos(self, request):
        rango = int(request.data.get("rango", 5))
        anio_actual = datetime.now().year
        existentes = set(
            CicloEscolar.objects.filter(anio_inicio__isnull=False, anio_fin__isnull=False)
            .values_list("anio_inicio", "anio_fin")
        )
        tipos = list(TipoPeriodo.objects.all())
        creados = []
        for offset in range(-rango, rango + 1):
            inicio = anio_actual + offset - 1
            fin = inicio + 1
            if (inicio, fin) in existentes:
                continue
            ciclo = CicloEscolar.objects.create(anio_inicio=inicio, anio_fin=fin)
            creados.append({"id": ciclo.id, "anio_inicio": inicio, "anio_fin": fin, "clave": ciclo.clave})
            for tipo in tipos:
                if tipo.nombre == TipoPeriodo.Tipo.SEMESTRAL:
                    numeros = [1, 2]
                elif tipo.nombre == TipoPeriodo.Tipo.CUATRIMESTRAL:
                    numeros = [1, 2, 3]
                else:
                    numeros = [1]
                for numero in numeros:
                    PeriodoAcademico.objects.get_or_create(
                        ciclo_escolar=ciclo,
                        tipo_periodo=tipo,
                        numero=numero,
                        defaults={"clave": f"{ciclo.clave}-{tipo.nombre[0]}{numero}"},
                    )
        return Response({"creados": creados, "total_creados": len(creados)})


class InscripcionPeriodoViewSet(viewsets.ModelViewSet):
    queryset = InscripcionPeriodo.objects.all().order_by("id")
    serializer_class = InscripcionPeriodoSerializer

    def get_queryset(self):
        qs = super().get_queryset().select_related("trayectoria_academica", "periodo_academico", "periodo_academico__ciclo_escolar", "periodo_academico__tipo_periodo")
        carrera_id = self.request.query_params.get("carrera_id")
        periodo_academico_id = self.request.query_params.get("periodo_academico_id")
        ciclo_escolar_id = self.request.query_params.get("ciclo_escolar_id")
        trayectoria_id = self.request.query_params.get("trayectoria_id")

        if carrera_id and carrera_id.isdigit():
            qs = qs.filter(trayectoria_academica__carrera_id=int(carrera_id))
        if periodo_academico_id and periodo_academico_id.isdigit():
            qs = qs.filter(periodo_academico_id=int(periodo_academico_id))
        if trayectoria_id and trayectoria_id.isdigit():
            qs = qs.filter(trayectoria_academica_id=int(trayectoria_id))
        if ciclo_escolar_id and ciclo_escolar_id.isdigit():
            qs = qs.filter(periodo_academico__ciclo_escolar_id=int(ciclo_escolar_id))
        return qs


class PlanEstudioViewSet(viewsets.ModelViewSet):
    queryset = PlanEstudio.objects.all().order_by("id")
    serializer_class = PlanEstudioSerializer


class MateriaViewSet(viewsets.ModelViewSet):
    queryset = Materia.objects.all().order_by("plan_estudio_id", "ciclo_numero", "id")
    serializer_class = MateriaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        plan_id = self.request.query_params.get("plan_estudio_id")
        if plan_id and plan_id.isdigit():
            qs = qs.filter(plan_estudio_id=int(plan_id))
        return qs


class CalificacionDetalleViewSet(viewsets.ModelViewSet):
    queryset = CalificacionDetalle.objects.all().order_by("id")
    serializer_class = CalificacionDetalleSerializer

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                "inscripcion_periodo",
                "catalogo_materia",
                "inscripcion_periodo__trayectoria_academica__alumno",
                "inscripcion_periodo__trayectoria_academica__carrera",
            )
        )
        if es_admin(self.request.user):
            return qs
        planteles = planteles_usuario(self.request.user)
        if planteles:
            qs = qs.filter(
                inscripcion_periodo__trayectoria_academica__carrera__plantel_id__in=planteles
            )
        inscripcion_periodo_id = self.request.query_params.get("inscripcion_periodo_id")
        materia_id = self.request.query_params.get("materia_id")
        if inscripcion_periodo_id and inscripcion_periodo_id.isdigit():
            qs = qs.filter(inscripcion_periodo_id=int(inscripcion_periodo_id))
        if materia_id and materia_id.isdigit():
            qs = qs.filter(catalogo_materia_id=int(materia_id))
        return qs

    @action(detail=False, methods=["get"], url_path="matriz")
    def matriz(self, request):
        carrera_id = request.query_params.get("carrera_id")
        periodo_academico_id = request.query_params.get("periodo_academico_id")
        materia_id = request.query_params.get("materia_id")
        ciclo_escolar = request.query_params.get("ciclo_escolar")

        if not (carrera_id and carrera_id.isdigit()):
            return Response({"detail": "carrera_id es requerido."}, status=400)
        if not (periodo_academico_id and periodo_academico_id.isdigit()):
            return Response({"detail": "periodo_academico_id es requerido."}, status=400)
        if not (materia_id and materia_id.isdigit()):
            return Response({"detail": "materia_id es requerido."}, status=400)

        planteles = planteles_usuario(request.user)
        if not _carrera_en_planteles(request.user, int(carrera_id), planteles):
            return Response(
                {"detail": "No tienes acceso a los registros de esa carrera/plantel."},
                status=403,
            )

        carrera_id_n = int(carrera_id)
        periodo_id_n = int(periodo_academico_id)
        materia_id_n = int(materia_id)

        inscripciones_qs = (
            InscripcionPeriodo.objects.filter(
                trayectoria_academica__carrera_id=carrera_id_n,
                periodo_academico_id=periodo_id_n,
            )
            .select_related("trayectoria_academica__alumno")
            .order_by("trayectoria_academica__alumno__matricula", "id")
        )
        if ciclo_escolar:
            inscripciones_qs = inscripciones_qs.filter(periodo_academico__ciclo_escolar__clave=ciclo_escolar)

        inscripciones = list(inscripciones_qs)
        if not inscripciones:
            return Response([])

        detalles = CalificacionDetalle.objects.filter(
            inscripcion_periodo_id__in=[x.id for x in inscripciones],
            catalogo_materia_id=materia_id_n,
        )
        detalle_by_inscripcion = {d.inscripcion_periodo_id: d for d in detalles}

        rows = []
        for ins in inscripciones:
            alumno = ins.trayectoria_academica.alumno
            det = detalle_by_inscripcion.get(ins.id)
            rows.append(
                {
                    "inscripcion_periodo_id": ins.id,
                    "calificacion_detalle_id": det.id if det else None,
                    "alumno_id": alumno.id,
                    "matricula": alumno.matricula,
                    "alumno_nombre": f"{alumno.nombres} {alumno.primer_apellido} {alumno.segundo_apellido}".strip(),
                    "calificacion_ordinaria": det.calificacion_ordinaria if det else None,
                    "extraordinario_1": det.extraordinario_1 if det else None,
                    "extraordinario_2": det.extraordinario_2 if det else None,
                    "calificacion_final": det.calificacion_final if det else None,
                    "calificacion_letra": det.calificacion_letra if det else "",
                }
            )

        return Response(rows)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        items = request.data.get("items", [])

        if not isinstance(items, list):
            return Response({"detail": "items debe ser una lista."}, status=400)

        created = []
        updated = []
        skipped = []
        errors = []

        cache_carrera: dict[str, Carrera] = {}
        cache_ciclo: dict[str, CicloEscolar] = {}
        cache_periodo: dict[str, PeriodoAcademico] = {}
        cache_materia: dict[str, Materia] = {}

        def get_carrera(valor: str) -> Carrera | None:
            valor = str(valor or "").strip()
            if not valor:
                return None
            if valor in cache_carrera:
                return cache_carrera[valor]
            qs = Carrera.objects.all()
            if valor.isdigit():
                qs = qs.filter(pk=int(valor))
            else:
                qs = qs.filter(nombre__iexact=valor)
            obj = qs.first()
            cache_carrera[valor] = obj
            return obj

        def get_ciclo(valor: str) -> CicloEscolar | None:
            valor = str(valor or "").strip()
            if not valor:
                return None
            if valor in cache_ciclo:
                return cache_ciclo[valor]
            obj = CicloEscolar.objects.filter(clave__iexact=valor).first()
            cache_ciclo[valor] = obj
            return obj

        def get_periodo(valor: str, ciclo: CicloEscolar | None, tipo_periodo_id: int | None) -> PeriodoAcademico | None:
            valor = str(valor or "").strip()
            if not valor:
                return None
            key = f"{valor}|{getattr(ciclo, 'id', '')}|{tipo_periodo_id or ''}"
            if key in cache_periodo:
                return cache_periodo[key]
            qs = PeriodoAcademico.objects.all()
            if valor.isdigit():
                qs = qs.filter(pk=int(valor))
            else:
                qs = qs.filter(clave__iexact=valor)
            if ciclo and ciclo.pk:
                qs = qs.filter(ciclo_escolar=ciclo)
            if tipo_periodo_id:
                qs = qs.filter(tipo_periodo_id=tipo_periodo_id)
            obj = qs.first()
            cache_periodo[key] = obj
            return obj

        def get_materia(valor: str, plan_estudio: PlanEstudio | None) -> Materia | None:
            valor = str(valor or "").strip()
            if not valor or not plan_estudio:
                return None
            if valor in cache_materia:
                return cache_materia[valor]
            qs = Materia.objects.filter(plan_estudio=plan_estudio)
            if valor.isdigit():
                qs = qs.filter(pk=int(valor))
            else:
                qs = qs.filter(clave_materia__iexact=valor)
            obj = qs.first()
            cache_materia[valor] = obj
            return obj

        planteles = planteles_usuario(request.user)

        for idx, item in enumerate(items):
            row_num = idx + 2
            try:
                matricula = str(item.get("matricula", "")).strip()
                if not matricula:
                    errors.append({"row": row_num, "matricula": matricula, "message": "La matrícula es requerida."})
                    continue

                carrera = get_carrera(item.get("carrera") or item.get("carrera_id") or "")
                ciclo = get_ciclo(item.get("ciclo_escolar") or item.get("ciclo_escolar_id") or "")
                periodo = get_periodo(item.get("periodo_academico") or item.get("periodo_academico_id") or "", ciclo, getattr(carrera, "tipo_periodo_id", None))
                materia = get_materia(item.get("materia") or item.get("materia_id") or "", getattr(carrera, "planes_estudio", None).first() if carrera else None)

                if not carrera:
                    errors.append({"row": row_num, "matricula": matricula, "message": "Carrera no encontrada en el Excel."})
                    continue
                if not ciclo:
                    errors.append({"row": row_num, "matricula": matricula, "message": "Ciclo escolar no encontrado en el Excel."})
                    continue
                if not periodo:
                    errors.append({"row": row_num, "matricula": matricula, "message": "Periodo académico no encontrado en el Excel."})
                    continue
                if not materia:
                    errors.append({"row": row_num, "matricula": matricula, "message": "Materia no encontrada en el Excel."})
                    continue

                if not es_admin(request.user) and not _carrera_en_planteles(request.user, carrera.id, planteles):
                    errors.append({"row": row_num, "matricula": matricula, "message": "No tienes acceso al plantel de esta carrera."})
                    continue

                alumno = Alumno.objects.filter(matricula=matricula).first()
                if not alumno:
                    errors.append({"row": row_num, "matricula": matricula, "message": "Alumno no encontrado."})
                    continue

                trayectoria = (
                    TrayectoriaAcademica.objects
                    .filter(alumno=alumno, carrera_id=carrera.id, es_actual=True)
                    .first()
                )
                if not trayectoria:
                    errors.append({"row": row_num, "matricula": matricula, "message": "El alumno no tiene trayectoria en la carrera indicada."})
                    continue

                inscripcion, _ = InscripcionPeriodo.objects.get_or_create(
                    trayectoria_academica=trayectoria,
                    periodo_academico=periodo,
                    defaults={"estatus": InscripcionPeriodo.ESTATUS_CURSANDO, "es_actual": True},
                )

                detalle = CalificacionDetalle.objects.filter(
                    inscripcion_periodo=inscripcion,
                    catalogo_materia=materia,
                ).first()

                calif_data = {}
                for field in ("calificacion_ordinaria", "extraordinario_1", "extraordinario_2", "calificacion_final"):
                    if field in item and item[field] is not None:
                        calif_data[field] = item[field]

                if detalle and _is_equal_calificacion(detalle, calif_data):
                    skipped.append({"row": row_num, "matricula": matricula, "calificacion_detalle_id": detalle.id})
                    continue

                detalle, was_created = CalificacionDetalle.objects.update_or_create(
                    inscripcion_periodo=inscripcion,
                    catalogo_materia=materia,
                    defaults=calif_data,
                )
                (created if was_created else updated).append({
                    "matricula": matricula,
                    "calificacion_detalle_id": detalle.id,
                })
            except Exception as e:
                errors.append({"row": row_num, "matricula": item.get("matricula", ""), "message": str(e)})

        return Response({"created": created, "updated": updated, "skipped": skipped, "errors": errors})


def _is_equal_calificacion(detalle: CalificacionDetalle, incoming: dict) -> bool:
    for field in ("calificacion_ordinaria", "extraordinario_1", "extraordinario_2", "calificacion_final"):
        current = getattr(detalle, field)
        incoming_value = incoming.get(field)
        if incoming_value in (None, ""):
            incoming_value = None
        if current != incoming_value:
            return False
    return True


def _is_equal_alumno(alumno: Alumno | None, incoming: dict) -> bool:
    if not alumno:
        return False
    for field in ("nombres", "primer_apellido", "segundo_apellido", "curp", "genero"):
        if str(getattr(alumno, field, "") or "") != str(incoming.get(field, "") or ""):
            return False
    if (alumno.fecha_nacimiento.isoformat() if alumno.fecha_nacimiento else None) != incoming.get("fecha_nacimiento"):
        return False
    if alumno.foto != incoming.get("foto"):
        return False
    return True


def _is_equal_domicilio(domicilio: Domicilio | None, incoming: dict) -> bool:
    if not domicilio:
        return not any(v for v in incoming.values())
    for k, v in incoming.items():
        if str(getattr(domicilio, k, "") or "") != str(v or ""):
            return False
    return True


def _is_equal_contacto(contacto: DatosContacto | None, incoming: dict) -> bool:
    if not contacto:
        return not any(v for v in incoming.values())
    for k, v in incoming.items():
        if str(getattr(contacto, k, "") or "") != str(v or ""):
            return False
    return True


def _procesar_foto_bulk(foto_value: str, matricula: str) -> str:
    if not foto_value:
        return ""

    if foto_value.startswith("data:image/"):
        try:
            header, b64data = foto_value.split(",", 1)
            ext = header.split(";")[0].split("/")[-1].lower()
            if ext not in ("png", "jpeg", "jpg", "gif", "webp"):
                ext = "jpg"
            filename = f"alumnos/{matricula}.{ext}"
            full_path = Path(settings.MEDIA_ROOT) / filename
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(base64.b64decode(b64data))
            return filename
        except Exception:
            return ""

    if foto_value.startswith("http://") or foto_value.startswith("https://"):
        return ""

    try:
        source = Path(foto_value)
        if not source.exists():
            return ""
        ext = source.suffix.lower().lstrip(".")
        if ext not in ("png", "jpeg", "jpg", "gif", "webp"):
            ext = "jpg"
        filename = f"alumnos/{matricula}.{ext}"
        full_path = Path(settings.MEDIA_ROOT) / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(source, "rb") as src, open(full_path, "wb") as dst:
            dst.write(src.read())
        return filename
    except Exception:
        return ""
