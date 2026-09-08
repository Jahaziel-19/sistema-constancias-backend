from rest_framework import generics, permissions
from rest_framework.response import Response

from uh_documentos.models import DocumentoEmitido
from uh_documentos.serializers import DocumentoPublicoSerializer


class DocumentoPublicoRetrieveView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = DocumentoPublicoSerializer
    lookup_field = "folio"
    queryset = DocumentoEmitido.objects.select_related("tipo_documento").filter(es_valido=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        calificaciones = None
        if instance.tipo_documento.categoria == "KARDEX" and instance.alumno_id:
            calificaciones = self._get_kardex_calificaciones(instance)
        serializer = self.get_serializer(instance)
        serializer.context["calificaciones"] = calificaciones
        return Response(serializer.data)

    def _get_kardex_calificaciones(self, doc: DocumentoEmitido) -> list[dict] | None:
        try:
            from uh_academico.models import (
                CalificacionDetalle,
                InscripcionPeriodo,
                Materia,
                PlanEstudio,
                TrayectoriaAcademica,
            )

            tray = (
                TrayectoriaAcademica.objects
                .filter(alumno_id=doc.alumno_id, es_actual=True)
                .first()
            )
            if not tray or not tray.carrera_id:
                return None

            plan = (
                PlanEstudio.objects
                .filter(carrera_id=tray.carrera_id)
                .order_by("-vigencia_inicio", "-version", "-id")
                .first()
            )

            califs_qs = (
                CalificacionDetalle.objects
                .filter(
                    inscripcion_periodo__trayectoria_academica__alumno_id=doc.alumno_id,
                )
                .select_related(
                    "catalogo_materia",
                    "inscripcion_periodo__periodo_academico__ciclo_escolar",
                )
                .order_by("-inscripcion_periodo__periodo_academico__fecha_inicio")
            )
            if plan:
                califs_qs = califs_qs.filter(catalogo_materia__plan_estudio_id=plan.id)

            calif_map: dict[int, dict[str, object]] = {}
            for cal in califs_qs:
                mat_id = cal.catalogo_materia_id
                if mat_id not in calif_map:
                    ins = cal.inscripcion_periodo
                    ciclo = getattr(getattr(ins, "periodo_academico", None), "ciclo_escolar", None)
                    periodo_label = (
                        getattr(getattr(ins, "periodo_academico", None), "clave", "")
                        or getattr(ciclo, "clave", "")
                    )
                    final = (
                        cal.calificacion_final
                        if cal.calificacion_final is not None
                        else (cal.calificacion_ordinaria if cal.calificacion_ordinaria is not None else 0)
                    )
                    calif_map[mat_id] = {
                        "periodo_label": periodo_label,
                        "materia": getattr(cal.catalogo_materia, "nombre_materia", ""),
                        "clave": getattr(cal.catalogo_materia, "clave_materia", ""),
                        "calificacion_ordinaria": cal.calificacion_ordinaria if cal.calificacion_ordinaria is not None else None,
                        "extraordinario_1": cal.extraordinario_1 if cal.extraordinario_1 is not None else None,
                        "extraordinario_2": cal.extraordinario_2 if cal.extraordinario_2 is not None else None,
                        "calificacion_final": final if final != 0 else None,
                        "calificacion_letra": cal.calificacion_letra or "",
                        "creditos": getattr(cal.catalogo_materia, "creditos", "") or None,
                    }

            items: list[dict[str, object]] = []
            if plan:
                materias_plan = (
                    Materia.objects
                    .filter(plan_estudio=plan)
                    .order_by("ciclo_numero", "clave_materia")
                )
                for mat in materias_plan:
                    cal = calif_map.get(mat.id)
                    items.append({
                        "ciclo_numero": getattr(mat, "ciclo_numero", None),
                        "periodo_label": cal["periodo_label"] if cal else "",
                        "materia": mat.nombre_materia,
                        "clave": mat.clave_materia,
                        "calificacion_ordinaria": cal["calificacion_ordinaria"] if cal else None,
                        "extraordinario_1": cal["extraordinario_1"] if cal else None,
                        "extraordinario_2": cal["extraordinario_2"] if cal else None,
                        "calificacion_final": cal["calificacion_final"] if cal else None,
                        "calificacion_letra": cal["calificacion_letra"] if cal else "",
                        "creditos": mat.creditos or None,
                    })
            else:
                for cal in calif_map.values():
                    items.append(cal)

            return items or None
        except Exception:
            return None
