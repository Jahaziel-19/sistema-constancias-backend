from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from uh_core.models import ConfiguracionInstitucional
from uh_documentos.document_handlers import ejecutar_handler_variables
from uh_documentos.models import CategoriaDocumento, DocumentoEmitido, TipoDocumento
from uh_documentos.pdf import try_build_reportlab
from uh_documentos.serializers import (
    CategoriaDocumentoSerializer,
    DocumentoEmitidoCreateSerializer,
    DocumentoEmitidoSerializer,
    TipoDocumentoSerializer,
)
from uh_documentos.services import crear_documento
from uh_documentos.pdf.context import build_render_context
from uh_auditoria.services import registrar_auditoria


class TipoDocumentoViewSet(viewsets.ModelViewSet):
    queryset = TipoDocumento.objects.all().order_by("id")
    serializer_class = TipoDocumentoSerializer


class DocumentoEmitidoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoEmitido.objects.select_related("tipo_documento", "plantel").all().order_by("-fecha_emision")
    serializer_class = DocumentoEmitidoSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        serializer = DocumentoEmitidoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tipo_documento = TipoDocumento.objects.get(pk=data["tipo_documento_id"])
        externo_payload = None
        if data.get("externo_nombres"):
            externo_payload = {
                "nombres": data.get("externo_nombres") or "",
                "apellidos": data.get("externo_apellidos") or "",
                "correo": data.get("externo_correo") or "",
                "telefono": data.get("externo_telefono") or "",
            }
        extra = {}
        descripcion = (data.get("descripcion_nombramiento") or "").strip()
        if descripcion:
            extra["descripcion_nombramiento"] = descripcion
        institucion = (data.get("institucion_otorgante") or "").strip()
        if institucion:
            extra["institucion_otorgante"] = institucion
        folio_sep = (data.get("folio_sep") or "").strip()
        if folio_sep:
            extra["folio_sep"] = folio_sep

        es_staff = bool(getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False))
        if not es_staff:
            from uh_usuarios.access import obtener_perfil, planteles_usuario

            perfil = obtener_perfil(request.user)
            if perfil and perfil.autoridad_id:
                data["autoridad_id"] = perfil.autoridad_id
            planteles = planteles_usuario(request.user)
            if planteles and data.get("plantel_id") not in planteles:
                data["plantel_id"] = sorted(planteles)[0]

        aprobado_usuario = bool(data.get("aprobado_directiva", False))
        if getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False):
            aprobado_usuario = True
        doc = crear_documento(
            tipo_documento=tipo_documento,
            plantel_id=data["plantel_id"],
            autoridad_id=data.get("autoridad_id"),
            alumno_id=data.get("alumno_id"),
            externo_payload=externo_payload,
            aprobado_directiva=aprobado_usuario,
            archivo=data.get("archivo"),
            extra=extra or None,
        )

        registrar_auditoria(
            request=request,
            accion="documento_emitido_creado",
            modelo_afectado="documentos_emitidos",
            registro_id=doc.id,
            detalles_cambio={"folio": doc.folio, "tipo_documento_id": doc.tipo_documento_id},
        )

        data = DocumentoEmitidoSerializer(doc).data
        return Response(data, status=status.HTTP_201_CREATED)

    def _obtener_pdf_bytes(self, doc: DocumentoEmitido) -> bytes:
        snapshot_academico = doc.snapshot_academico if isinstance(doc.snapshot_academico, dict) else {}
        snapshot_extra = {
            k: snapshot_academico.get(k)
            for k in ("descripcion_nombramiento", "institucion_otorgante", "folio_sep")
            if snapshot_academico.get(k)
        }
        try:
            handler_campos, handler_repeticiones = ejecutar_handler_variables(
                tipo_documento=doc.tipo_documento,
                trayectoria=doc.alumno and (
                    doc.alumno.trayectorias.filter(es_actual=True).select_related("carrera__plantel", "carrera__tipo_periodo", "estatus_academico").first()
                ),
                aprobado_directiva=doc.aprobado_directiva,
                extra=snapshot_extra,
            )
        except Exception:
            handler_campos, handler_repeticiones = {}, {}

        alumno = None
        trayectoria = None
        plantel = doc.plantel
        autoridad = None
        if doc.alumno_id:
            try:
                from uh_academico.models import Alumno, TrayectoriaAcademica
                alumno = Alumno.objects.get(pk=doc.alumno_id)
                trayectoria = (
                    TrayectoriaAcademica.objects
                    .filter(alumno_id=doc.alumno_id, es_actual=True)
                    .select_related("carrera", "estatus_academico")
                    .first()
                )
                if trayectoria and trayectoria.carrera and trayectoria.carrera.plantel:
                    plantel = trayectoria.carrera.plantel
            except Exception:
                alumno = None
                trayectoria = None
        if plantel:
            try:
                from uh_core.models import PlantelAutoridad
                pa = (
                    PlantelAutoridad.objects
                    .filter(plantel_id=plantel.id)
                    .select_related("autoridad", "autoridad__contacto")
                    .first()
                )
                if pa and pa.autoridad:
                    autoridad = pa.autoridad
            except Exception:
                autoridad = None

        kardex_preload = None
        try:
            ctx = build_render_context(
                doc,
                extra_campos=handler_campos or None,
                extra_repeticiones=handler_repeticiones or None,
                plantel=plantel,
                autoridad=autoridad,
                alumno=alumno,
                trayectoria=trayectoria,
                kardex_preload=kardex_preload,
            )
        except Exception:
            ctx = None

        tipo_key: str | None = None
        try:
            from uh_documentos.document_handlers import get_handler
            h = get_handler(doc.tipo_documento) if doc.tipo_documento else None
            if h is not None:
                tipo_key = getattr(h, "key", None)
        except Exception:
            tipo_key = None
        if not tipo_key:
            return b""

        fields = dict(ctx.fields or {}) if ctx is not None else {}
        fields.setdefault("folio", doc.folio or "")
        fields.setdefault("folio_verif", doc.folio or "")
        fields.setdefault("url_verificacion", "")
        fields.setdefault("qr_png_base64", "")

        if snapshot_academico.get("descripcion_nombramiento") and not fields.get("descripcion_nombramiento"):
            fields["descripcion_nombramiento"] = snapshot_academico["descripcion_nombramiento"]
        if snapshot_academico.get("institucion_otorgante") and not fields.get("institucion_otorgante"):
            fields["institucion_otorgante"] = snapshot_academico["institucion_otorgante"]
        if snapshot_academico.get("folio_sep") and not fields.get("folio_sep"):
            fields["folio_sep"] = snapshot_academico["folio_sep"]

        if plantel:
            dom = getattr(plantel, "domicilio", None)
            municipio = getattr(dom, "municipio", "") or ""
            estado = getattr(dom, "estado", "") or ""
            lugar = ", ".join([p for p in [municipio, estado] if p]) or "Huauchinango, Puebla"
            from datetime import date
            from uh_documentos.pdf.context import lugar_fecha
            fields["lugar_fecha"] = lugar_fecha(
                municipio=municipio,
                estado=estado,
                dt=date.today(),
                default=lugar,
            )

        if alumno:
            fields["nombre"] = f"{alumno.nombres} {alumno.primer_apellido} {alumno.segundo_apellido}".strip()
            fields["matricula"] = alumno.matricula or ""
            if alumno.foto and alumno.foto.path:
                fields["foto_path"] = alumno.foto.path
            elif alumno.foto and alumno.foto.url:
                try:
                    from django.conf import settings
                    from pathlib import Path
                    media_root = Path(settings.MEDIA_ROOT)
                    relative_url = Path(alumno.foto.url.lstrip("/"))
                    abs_path = media_root / relative_url
                    if abs_path.exists():
                        fields["foto_path"] = str(abs_path)
                    else:
                        fields["foto_path"] = alumno.foto.url
                except Exception:
                    fields["foto_path"] = alumno.foto.url
            if trayectoria:
                nivel = trayectoria.nivel_actual or 1
                fields["nivel_actual_ordinal"] = f"{nivel}°"
                fields["ciclo_nombre"] = getattr(trayectoria, "ciclo_nombre", None) or getattr(trayectoria.carrera.tipo_periodo, "nombre", "") or "semestral"
                fields["carrera_nombre"] = trayectoria.carrera.nombre if trayectoria.carrera else ""
                fields["turno"] = getattr(trayectoria, "turno", None) or ""
                fields["modalidad"] = getattr(trayectoria, "modalidad", None) or ""
                if trayectoria.carrera and trayectoria.carrera.plantel_id and not fields.get("plantel_nombre"):
                    fields["plantel_nombre"] = trayectoria.carrera.plantel.nombre
                try:
                    from uh_academico.models import InscripcionPeriodo
                    insc_actual = InscripcionPeriodo.objects.filter(
                        trayectoria_academica_id=trayectoria.id,
                        es_actual=True,
                    ).select_related("periodo_academico__ciclo_escolar").first()
                    if insc_actual and insc_actual.periodo_academico:
                        pa = insc_actual.periodo_academico
                        fields["periodo_nombre"] = pa.clave or ""
                        fields["ciclo_escolar_clave"] = pa.ciclo_escolar.clave if pa.ciclo_escolar else ""
                        if pa.fecha_inicio:
                            fields["periodo_fecha_inicio"] = pa.fecha_inicio.strftime("%d/%m/%Y")
                        if pa.fecha_fin:
                            fields["periodo_fecha_fin"] = pa.fecha_fin.strftime("%d/%m/%Y")
                except Exception:
                    pass
        elif doc.externo_id:
            try:
                externo = doc.externo
                if externo:
                    fields["nombre"] = f"{externo.nombres or ''} {externo.primer_apellido or ''} {externo.segundo_apellido or ''}".strip()
            except Exception:
                pass

        if autoridad:
            fields["firmante"] = f"{autoridad.titulo or ''} {autoridad.nombres or ''} {autoridad.apellidos or ''}".strip()
            fields["cargo_firmante"] = autoridad.cargo or ""
            fields["cargo_firmante_texto"] = autoridad.cargo or ""
            if autoridad.contacto:
                fields["correo_firmante"] = autoridad.contacto.correo_electronico or ""
                fields["cel_firmante"] = autoridad.contacto.celular or ""
                fields["tel_firmante"] = autoridad.contacto.telefono or ""

        if plantel:
            fields["plantel_nombre"] = plantel.nombre
            fields["institucion_clave"] = plantel.rgp or plantel.clave_plantel or ""
            fields["registro_sep"] = plantel.registro_sep or ""
            fields["plantel_clave"] = plantel.clave_plantel or ""
            try:
                dom = getattr(plantel, "domicilio", None)
                if dom:
                    partes = [p for p in [dom.calle, dom.numero_exterior, dom.colonia, dom.codigo_postal, dom.municipio, dom.estado] if p]
                    fields["direccion_plantel"] = ", ".join(partes)
                else:
                    fields["direccion_plantel"] = ""
                contacto_plantel = getattr(plantel, "contacto", None)
                fields["telefono_plantel"] = getattr(contacto_plantel, "telefono", "") or ""
                fields["correo_plantel"] = getattr(contacto_plantel, "correo_electronico", "") or ""
                fields["web_plantel"] = plantel.pagina_web or ""
            except Exception:
                fields["direccion_plantel"] = ""
                fields["telefono_plantel"] = ""
                fields["correo_plantel"] = ""
                fields["web_plantel"] = ""

        autoridad_firmante_nombre = fields.get("firmante") or None
        autoridad_firmante_cargo = fields.get("cargo_firmante") or None
        autoridad_firmante_correo = fields.get("correo_firmante") or None
        autoridad_firmante_cel = fields.get("cel_firmante") or None

        if tipo_key == "kardex":
            try:
                from uh_academico.models import PlanEstudio, Materia, InscripcionPeriodo, CalificacionDetalle
                local_tray = trayectoria
                if not local_tray and doc.alumno_id:
                    local_tray = (
                        TrayectoriaAcademica.objects
                        .filter(alumno_id=doc.alumno_id, es_actual=True)
                        .first()
                    )
                if local_tray and local_tray.carrera_id:
                    plan = (
                        PlanEstudio.objects
                        .filter(carrera_id=local_tray.carrera_id)
                        .order_by("-vigencia_inicio", "-version")
                        .first()
                    )
                    califs_qs = (
                        CalificacionDetalle.objects
                        .filter(
                            inscripcion_periodo__trayectoria_academica=local_tray,
                            inscripcion_periodo__es_actual=True,
                        )
                        .select_related(
                            "catalogo_materia",
                            "inscripcion_periodo__periodo_academico__ciclo_escolar",
                        )
                        .order_by("-inscripcion_periodo__periodo_academico__fecha_inicio")
                    )
                    calif_map: dict[int, dict[str, Any]] = {}
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
                                "ordinario": cal.calificacion_ordinaria if cal.calificacion_ordinaria is not None else "",
                                "extra_1": cal.extraordinario_1 if cal.extraordinario_1 is not None else "",
                                "extra_2": cal.extraordinario_2 if cal.extraordinario_2 is not None else "",
                                "final": final if final != 0 else "",
                                "calificacion_letra": cal.calificacion_letra or "",
                                "creditos": getattr(cal.catalogo_materia, "creditos", "") or "",
                            }
                    materias_items: list[dict[str, Any]] = []
                    periodos_items: list[dict[str, Any]] = []
                    seen_periodos: set[str] = set()
                    if plan:
                        materias_plan = (
                            Materia.objects
                            .filter(plan_estudio=plan)
                            .order_by("ciclo_numero", "clave_materia")
                        )
                        for mat in materias_plan:
                            cal = calif_map.get(mat.id)
                            materias_items.append({
                                "ciclo_numero": getattr(mat, "ciclo_numero", None),
                                "periodo_label": cal["periodo_label"] if cal else "",
                                "materia": mat.nombre_materia,
                                "clave": mat.clave_materia,
                                "ordinario": cal["ordinario"] if cal else "",
                                "extra_1": cal["extra_1"] if cal else "",
                                "extra_2": cal["extra_2"] if cal else "",
                                "final": cal["final"] if cal else "",
                                "calificacion_letra": cal["calificacion_letra"] if cal else "",
                                "creditos": mat.creditos or "",
                            })
                            if cal and cal["periodo_label"] and cal["periodo_label"] not in seen_periodos:
                                periodos_items.append({"_periodo_label": cal["periodo_label"]})
                                seen_periodos.add(cal["periodo_label"])
                    else:
                        for cal in calif_map.values():
                            materias_items.append(cal)
                            if cal["periodo_label"]:
                                periodos_items.append({"_periodo_label": cal["periodo_label"]})
                    fields["materias_items"] = materias_items
                    fields["periodos_items"] = periodos_items
                    finals = [float(m["final"]) for m in materias_items if m.get("final") not in ("", None)]
                    credits = sum(float(m["creditos"]) for m in materias_items if m.get("creditos") not in ("", None))
                    kardex_preload = {
                        "materias_items": materias_items,
                        "periodos_items": periodos_items,
                        "total_creditos": credits,
                        "total_materias": len(materias_items),
                        "promedio": round(sum(finals) / len(finals), 2) if finals else None,
                    }
            except Exception:
                kardex_preload = None
        if "materias_items" in fields and fields.get("materias_items") is not None:
            try:
                finals = []
                credits = 0.0
                for m in fields.get("materias_items", []):
                    fv = m.get("final") or m.get("cal_final")
                    if fv != "" and fv is not None:
                        try:
                            finals.append(float(fv))
                        except Exception:
                            pass
                    cr = m.get("creditos") or m.get("cred")
                    if cr != "" and cr is not None:
                        try:
                            credits += float(cr)
                        except Exception:
                            pass
                if finals:
                    fields["promedio_general"] = round(sum(finals) / len(finals), 2)
                if credits:
                    fields["creditos_acumulados"] = int(credits) if credits == int(credits) else round(credits, 2)
            except Exception:
                pass
        try:
            cfg = ConfiguracionInstitucional.objects.first()
            if cfg:
                fields["institucion_nombre"] = cfg.nombre_institucion
        except Exception:
            pass
        logo_path = ""
        try:
            logo_path = str(settings.MEDIA_ROOT / "logos" / "logo_hispana.png")
        except Exception:
            logo_path = ""
        firmante_firma_path = None
        try:
            if autoridad and autoridad.firma_digital and autoridad.firma_digital.path:
                firmante_firma_path = str(autoridad.firma_digital.path)
        except Exception:
            firmante_firma_path = None

        try:
            from uh_documentos.pdf.qr import build_qr_verification_data
            qr_data = build_qr_verification_data(folio=doc.folio or "")
            fields["qr_png_base64"] = qr_data.get("qr_png_base64") or ""
            fields["url_verificacion"] = qr_data.get("url_verificacion") or ""
        except Exception:
            fields["qr_png_base64"] = ""
            fields["url_verificacion"] = ""

        rl_bytes = try_build_reportlab(
            fields,
            tipo_key=tipo_key,
            logo_path=logo_path or None,
            plantel_obj=plantel,
            firmante_nombre=autoridad_firmante_nombre if autoridad_firmante_nombre else None,
            firmante_cargo=autoridad_firmante_cargo if autoridad_firmante_cargo else None,
            firmante_correo=autoridad_firmante_correo if autoridad_firmante_correo else None,
            firmante_cel=autoridad_firmante_cel if autoridad_firmante_cel else None,
            firmante_firma_path=firmante_firma_path,
        )
        if rl_bytes:
            return rl_bytes
        return b""

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf_documento(self, request, pk=None):
        doc = self.get_object()
        pdf_bytes = b""
        err_detail = ""
        try:
            pdf_bytes = self._obtener_pdf_bytes(doc)
        except Exception as e:
            import traceback
            err_detail = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        if not pdf_bytes:
            detail = err_detail or "No fue posible generar el PDF para este documento."
            return Response({"detail": detail}, status=404)
        filename = f"{doc.folio}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Length"] = str(len(pdf_bytes))
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp

    @action(detail=True, methods=["get"], url_path="pdf/download")
    def pdf_documento_download(self, request, pk=None):
        doc = self.get_object()
        pdf_bytes = b""
        err_detail = ""
        try:
            pdf_bytes = self._obtener_pdf_bytes(doc)
        except Exception as e:
            import traceback
            err_detail = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        if not pdf_bytes:
            detail = err_detail or "No fue posible generar el PDF para este documento."
            return Response({"detail": detail}, status=404)
        filename = f"{doc.folio}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Length"] = str(len(pdf_bytes))
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    @action(detail=True, methods=["get"])
    def archivo(self, request, pk=None):
        try:
            doc = self.get_object()
        except Http404:
            raise
        if not doc.archivo:
            return Response({"detail": "No hay archivo asociado."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(doc.archivo.open("rb"), as_attachment=True, filename=doc.archivo.name.split("/")[-1])


class CategoriaDocumentoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaDocumento.objects.all().order_by("id")
    serializer_class = CategoriaDocumentoSerializer