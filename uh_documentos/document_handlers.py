from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rest_framework.exceptions import ValidationError

from uh_academico.models import TrayectoriaAcademica
from uh_documentos.models import TipoDocumento


@dataclass
class DocumentoContextoBase:
    tipo_documento: TipoDocumento
    trayectoria: TrayectoriaAcademica | None
    aprobado_directiva: bool
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentoHandlerResult:
    campos: dict[str, Any] = field(default_factory=dict)
    repeticiones: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)


class BaseDocumentoHandler:
    key: str = ""
    nombre_tipo_documento: str = ""
    plantilla: str = ""

    def puede_manejar(self, tipo_documento: TipoDocumento) -> bool:
        nombre = (tipo_documento.nombre or "").strip()
        return bool(nombre and nombre.lower() == self.nombre_tipo_documento.lower())

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        return []

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        return DocumentoHandlerResult()

    def asegurar_plantilla(self, tipo_documento: TipoDocumento) -> None:
        if not tipo_documento.plantilla and self.plantilla:
            tipo_documento.plantilla = self.plantilla
            tipo_documento.save(update_fields=["plantilla"])


def _requiere_estatus(trayectoria: TrayectoriaAcademica | None, estatus_permitidos: set[str]) -> str | None:
    if not trayectoria or not trayectoria.estatus_academico:
        return "No se encontró trayectoria académica o estatus académico asociado."
    nombre = (trayectoria.estatus_academico.nombre or "").strip()
    if not nombre:
        return "No se encontró estatus académico asociado."
    permitidos = {e.lower() for e in estatus_permitidos}
    if nombre.lower() not in permitidos:
        return f"El estatus académico actual '{nombre}' no cumple los requisitos para este documento."
    return None


class ConstanciaEstudiosHandler(BaseDocumentoHandler):
    key = "constancia_estudios"
    nombre_tipo_documento = "Constancia de Estudios"
    plantilla = "pdf/constancias/estudio.html"

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        err = _requiere_estatus(ctx.trayectoria, {"activo", "regular", "alumno regular", "inscrito"})
        if err:
            errores.append(err)
        return errores

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        campos: dict[str, Any] = {}
        tray = ctx.trayectoria
        if tray:
            turno = ctx.extra.get("turno") or (getattr(tray, "turno", None) or "")
            modalidad = ctx.extra.get("modalidad") or (getattr(tray, "modalidad", None) or "")
            campos.update({
                "turno": turno or "Escolarizado",
                "modalidad": modalidad or "Escolarizada",
            })
        return DocumentoHandlerResult(campos=campos)


class ConstanciaEgresoHandler(BaseDocumentoHandler):
    key = "constancia_egreso"
    nombre_tipo_documento = "Constancia de Egreso"
    plantilla = "pdf/constancias/egreso.html"

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        err = _requiere_estatus(ctx.trayectoria, {"egresado", "titulado"})
        if err:
            errores.append(err)
        return errores

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        campos: dict[str, Any] = {}
        tray = ctx.trayectoria
        if tray and tray.carrera:
            titulo = getattr(tray.carrera, "titulo_otorgado", None) or f"Titulado(a) en {tray.carrera.nombre}"
            campos["titulo_otorgado"] = titulo
        return DocumentoHandlerResult(campos=campos)


class ConstanciaFinalizacionTitulacionHandler(BaseDocumentoHandler):
    key = "constancia_finalizacion_titulacion"
    nombre_tipo_documento = "Constancia de Finalizacion con Titulacion en Proceso"
    plantilla = "pdf/constancias/egreso.html"

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        err = _requiere_estatus(ctx.trayectoria, {"egresado", "titulado"})
        if err:
            errores.append(err)
        if ctx.trayectoria and not getattr(ctx.trayectoria, "titulacion_en_proceso", False):
            errores.append("La trayectoria académica no cuenta con titulación en proceso.")
        return errores


class ConstanciaFinalizacionSinTitulacionHandler(BaseDocumentoHandler):
    key = "constancia_finalizacion_sin_titulacion"
    nombre_tipo_documento = "Finalizacion de estudios sin proceso de titulacion"
    plantilla = "pdf/constancias/egreso.html"

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        err = _requiere_estatus(ctx.trayectoria, {"egresado", "titulado"})
        if err:
            errores.append(err)
        if ctx.trayectoria and getattr(ctx.trayectoria, "titulacion_en_proceso", False):
            errores.append("La trayectoria académica ya cuenta con titulación en proceso.")
        return errores


class KardexHandler(BaseDocumentoHandler):
    key = "kardex"
    nombre_tipo_documento = "Kardex General"
    plantilla = "kardex.html"

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        if not ctx.trayectoria:
            errores.append("No se encontró trayectoria académica asociada.")
        return errores

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        campos: dict[str, Any] = {}
        repeticiones: dict[str, list[dict[str, Any]]] = {}
        tray = ctx.trayectoria
        if not tray:
            return DocumentoHandlerResult(campos=campos, repeticiones=repeticiones)
        try:
            from uh_academico.models import PlanEstudio, Materia, InscripcionPeriodo, CalificacionDetalle

            plan = None
            if tray.carrera_id:
                plan = (
                    PlanEstudio.objects
                    .filter(carrera_id=tray.carrera_id)
                    .order_by("-vigencia_inicio", "-version")
                    .first()
                )

            califs_qs = (
                CalificacionDetalle.objects
                .filter(
                    inscripcion_periodo__trayectoria_academica=tray,
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

            if plan:
                materias_plan = (
                    Materia.objects
                    .filter(plan_estudio=plan)
                    .order_by("ciclo_numero", "clave_materia")
                )
                seen_periodos: set[str] = set()
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

            repeticiones["materias_items"] = materias_items
            repeticiones["periodos_items"] = periodos_items
            campos["materias_items"] = materias_items
        except Exception:
            pass
        return DocumentoHandlerResult(campos=campos, repeticiones=repeticiones)


class DiplomaHandler(BaseDocumentoHandler):
    key = "diploma"
    nombre_tipo_documento = "Diploma"
    plantilla = ""

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        err = _requiere_estatus(ctx.trayectoria, {"egresado", "titulado"})
        if err:
            errores.append(err)
        return errores

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        campos: dict[str, Any] = {}
        tray = ctx.trayectoria
        if tray and tray.carrera:
            campos["titulo_otorgado"] = getattr(tray.carrera, "titulo_otorgado", None) or f"Titulado(a) en {tray.carrera.nombre}"
        return DocumentoHandlerResult(campos=campos)


class ReconocimientoHandler(BaseDocumentoHandler):
    key = "reconocimiento"
    nombre_tipo_documento = "Reconocimiento"
    plantilla = ""

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        return []

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        return DocumentoHandlerResult(campos={}, repeticiones={})


class DiplomaReconocimientoHandler(BaseDocumentoHandler):
    key = "diploma_reconocimiento"
    nombre_tipo_documento = "Diploma y Reconocimiento"
    plantilla = ""

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        descripcion = (ctx.extra.get("descripcion_nombramiento") or "").strip()
        if not descripcion:
            errores.append("Se requiere la descripción del nombramiento para este documento.")
        return errores

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        campos: dict[str, Any] = {}
        descripcion = (ctx.extra.get("descripcion_nombramiento") or "").strip()
        institucion = (ctx.extra.get("institucion_otorgante") or "").strip()
        if descripcion:
            campos["descripcion_nombramiento"] = descripcion
        if institucion:
            campos["institucion_otorgante"] = institucion
        return DocumentoHandlerResult(campos=campos, repeticiones={})


class TituloHandler(BaseDocumentoHandler):
    key = "titulo"
    nombre_tipo_documento = "Título Profesional"
    plantilla = ""

    def validar(self, ctx: DocumentoContextoBase) -> list[str]:
        errores: list[str] = []
        folio_sep = (ctx.extra.get("folio_sep") or "").strip()
        if not folio_sep:
            errores.append("Se requiere el folio SEP para emitir un Título Profesional.")
        return errores

    def construir_variables(self, ctx: DocumentoContextoBase) -> DocumentoHandlerResult:
        campos: dict[str, Any] = {}
        folio_sep = (ctx.extra.get("folio_sep") or "").strip()
        if folio_sep:
            campos["folio_sep"] = folio_sep
        return DocumentoHandlerResult(campos=campos, repeticiones={})


HANDLERS: list[BaseDocumentoHandler] = [
    ConstanciaEstudiosHandler(),
    ConstanciaEgresoHandler(),
    ConstanciaFinalizacionTitulacionHandler(),
    ConstanciaFinalizacionSinTitulacionHandler(),
    KardexHandler(),
    DiplomaHandler(),
    ReconocimientoHandler(),
    DiplomaReconocimientoHandler(),
    TituloHandler(),
]


def registrar_handler(handler: BaseDocumentoHandler) -> None:
    HANDLERS.append(handler)


def get_handler(tipo_documento: TipoDocumento) -> BaseDocumentoHandler | None:
    for h in HANDLERS:
        if h.puede_manejar(tipo_documento):
            return h
    return None


def validar_requisitos(
    *,
    tipo_documento: TipoDocumento,
    trayectoria: TrayectoriaAcademica | None,
    aprobado_directiva: bool,
    extra: dict[str, Any] | None = None,
) -> None:
    handler = get_handler(tipo_documento)
    ctx = DocumentoContextoBase(
        tipo_documento=tipo_documento,
        trayectoria=trayectoria,
        aprobado_directiva=aprobado_directiva,
        extra=extra or {},
    )
    errores: list[str] = []
    if handler:
        errores.extend(handler.validar(ctx))
    reglas = tipo_documento.reglas_validacion or {}
    if reglas.get("requiere_aprobacion_directiva") and not aprobado_directiva:
        errores.append("Este tipo de documento requiere aprobación directiva.")
    if errores:
        raise ValidationError(errores)


def ejecutar_handler_variables(
    *,
    tipo_documento: TipoDocumento,
    trayectoria: TrayectoriaAcademica | None,
    aprobado_directiva: bool,
    extra: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    handler = get_handler(tipo_documento)
    if not handler:
        return {}, {}
    ctx = DocumentoContextoBase(
        tipo_documento=tipo_documento,
        trayectoria=trayectoria,
        aprobado_directiva=aprobado_directiva,
        extra=extra or {},
    )
    try:
        handler.asegurar_plantilla(tipo_documento)
    except Exception:
        pass
    result = handler.construir_variables(ctx)
    return result.campos or {}, result.repeticiones or {}
