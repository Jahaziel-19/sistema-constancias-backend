from __future__ import annotations

from typing import Any, Mapping

from uh_documentos.pdf.builders.base_builder import BaseDocumentBuilder
from uh_documentos.pdf.components.base import RLComponents



class ConstanciaFinalizacionTitulacionBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "CONSTANCIA DE FINALIZACIÓN CON TITULACIÓN EN PROCESO"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Constancia de Finalizacion con Titulacion en Proceso")

    def body_segments(self) -> list[tuple[str, bool]]:
        return _constancia_finalizacion_titulacion_body(self.fields)

    def datos_rows(self) -> list[tuple[str, str]]:
        return _datos_rows(self.fields)


class ConstanciaFinalizacionSinTitulacionBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "CONSTANCIA DE FINALIZACIÓN DE ESTUDIOS SIN PROCESO DE TITULACIÓN"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Finalizacion de estudios sin proceso de titulacion")

    def body_segments(self) -> list[tuple[str, bool]]:
        return _constancia_finalizacion_sin_titulacion_body(self.fields)

    def datos_rows(self) -> list[tuple[str, str]]:
        return _datos_rows(self.fields)


class ConstanciaEgresoBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "CONSTANCIA DE EGRESO"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Constancia de Egreso")

    def body_segments(self) -> list[tuple[str, bool]]:
        return _constancia_egreso_body(self.fields)

    def datos_rows(self) -> list[tuple[str, str]]:
        return _datos_rows(self.fields)


class ConstanciaEstudiosBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "CONSTANCIA DE ESTUDIOS"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Constancia de Estudios")

    def body_segments(self) -> list[tuple[str, bool]]:
        return _constancia_estudios_body(self.fields)

    def datos_rows(self) -> list[tuple[str, str]]:
        return _datos_rows(self.fields)


def _constancia_egreso_body(fields: Mapping[str, Any]) -> list[tuple[str, bool]]:
    nombre = str(fields.get("nombre") or "Nombre Completo del Estudiante")
    carrera = str(fields.get("carrera_nombre") or "Licenciatura en Derecho Corporativo")
    matricula = str(fields.get("matricula") or "")
    periodo = str(fields.get("periodo_nombre") or fields.get("plan_vigencia") or "")
    fecha_egreso = str(fields.get("fecha_egreso") or fields.get("fecha_titulacion") or "")
    turno = str(fields.get("turno") or "")
    modalidad = str(fields.get("modalidad") or "")

    parts: list[tuple[str, bool]] = []
    parts.append(("Por medio de este conducto se hace constar que", False))
    parts.append((f" {nombre} ", True))
    parts.append(("ha egresado de la carrera de", False))
    parts.append((f" {carrera} ", True))
    if matricula:
        parts.append((" de esta Institución, con matrícula ", False))
        parts.append((matricula, True))
    else:
        parts.append((" de esta Institución.", False))
    if periodo:
        parts.append((" En el periodo ", False))
        parts.append((periodo, True))
        parts.append((".", False))
    if fecha_egreso:
        parts.append((" Con fecha de egreso: ", False))
        parts.append((fecha_egreso, True))
        parts.append((".", False))
    if turno:
        parts.append((" Turno: ", False))
        parts.append((turno, True))
        parts.append((".", False))
    if modalidad:
        parts.append((" Modalidad: ", False))
        parts.append((modalidad, True))
        parts.append((".", False))
    parts.append((" Cumpliendo con todos los requisitos establecidos por el plan de estudios correspondiente. Sin otro particular por el momento.", False))
    return parts


def _constancia_finalizacion_titulacion_body(fields: Mapping[str, Any]) -> list[tuple[str, bool]]:
    nombre = str(fields.get("nombre") or "Nombre Completo del Estudiante")
    carrera = str(fields.get("carrera_nombre") or "Licenciatura en Derecho Corporativo")
    periodo = str(fields.get("periodo_nombre") or fields.get("plan_vigencia") or "")

    parts: list[tuple[str, bool]] = []
    parts.append(("Por medio del presente hago de su conocimiento que en nuestro sistema escolar consta que el (la) alumno(a):", False))
    parts.append((f" {nombre} ", True))
    parts.append(("Concluyo satisfactoriamente sus estudios de:", False))
    parts.append((f" {carrera} ", True))
    if periodo:
        parts.append(("En el periodo:", False))
        parts.append((f" {periodo} ", True))
    parts.append(("Se extiende la presente como constancia, que el proceso de su Título se encuentra en trámite ante la Secretaria de Educación Pública Federal.", False))
    return parts


def _constancia_finalizacion_sin_titulacion_body(fields: Mapping[str, Any]) -> list[tuple[str, bool]]:
    nombre = str(fields.get("nombre") or "Nombre Completo del Estudiante")
    carrera = str(fields.get("carrera_nombre") or "Licenciatura en Derecho Corporativo")
    periodo = str(fields.get("periodo_nombre") or fields.get("plan_vigencia") or "")

    parts: list[tuple[str, bool]] = []
    parts.append(("Por medio del presente hago de su conocimiento que en nuestro sistema escolar consta que el (la) alumno(a):", False))
    parts.append((f" {nombre} ", True))
    parts.append(("Concluyo satisfactoriamente sus estudios de:", False))
    parts.append((f" {carrera} ", True))
    if periodo:
        parts.append(("En el periodo:", False))
        parts.append((f" {periodo} ", True))
    parts.append(("Se extiende la presente como constancia de finalización de estudios, sin proceso de titulación.", False))
    return parts


def _constancia_estudios_body(fields: Mapping[str, Any]) -> list[tuple[str, bool]]:
    nombre = str(fields.get("nombre") or "Nombre Completo del Estudiante")
    nivel_ordinal = str(fields.get("nivel_actual_ordinal") or fields.get("nivel_actual") or "")
    if not nivel_ordinal:
        nivel_ordinal = "1°"
    ciclo = str(fields.get("ciclo_nombre") or "semestral").strip().lower()
    if ciclo == "semestral":
        ciclo = "semestre"
    elif ciclo == "cuatrimestral":
        ciclo = "cuatrimestre"
    carrera = str(fields.get("carrera_nombre") or "Licenciatura en Derecho Corporativo")
    matricula = str(fields.get("matricula") or "")
    turno = str(fields.get("turno") or "")
    modalidad = str(fields.get("modalidad") or "")

    parts: list[tuple[str, bool]] = []
    parts.append(("Por medio de este conducto se hace constar que del expediente escolar de", False))
    parts.append((f" {nombre} ", True))
    parts.append(("se encuentra inscrita(o) en el ", False))
    parts.append((f"{nivel_ordinal} {ciclo}".strip(), True))
    parts.append((" de la ", False))
    parts.append((carrera, True))
    parts.append((", en esta Institución, con matrícula ", False))
    if matricula:
        parts.append((matricula, True))
    extra_commas = False
    if turno:
        parts.append((", ", False))
        parts.append((turno, True))
        extra_commas = True
    if modalidad:
        parts.append((", ", False))
        parts.append((modalidad, True))
        extra_commas = True
    if not extra_commas:
        parts.append((".", False))
    else:
        parts.append((". ", False))
    parts.append(("Se extiende la presente a solicitud de la interesada y para los fines que crea convenientes dentro del marco de la Ley. Sin otro particular por el momento.", False))
    return parts


def _datos_rows(fields: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    periodo = str(fields.get("periodo_nombre") or fields.get("plan_vigencia") or "")
    if periodo:
        rows.append(("Periodo", periodo))
    turno = str(fields.get("turno") or "")
    if turno:
        rows.append(("Turno", turno))
    modalidad = str(fields.get("modalidad") or "")
    if modalidad:
        rows.append(("Modalidad", modalidad))
    ciclo_escolar = str(fields.get("ciclo_escolar_clave") or "")
    if ciclo_escolar:
        rows.append(("Ciclo escolar", ciclo_escolar))
    periodo_inicio = str(fields.get("periodo_fecha_inicio") or "")
    periodo_fin = str(fields.get("periodo_fecha_fin") or "")
    if periodo_inicio and periodo_fin:
        rows.append(("Periodo del", f"{periodo_inicio} al {periodo_fin}"))
    elif periodo_inicio:
        rows.append(("Fecha inicio", periodo_inicio))
    elif periodo_fin:
        rows.append(("Fecha fin", periodo_fin))
    return rows


def build_constancia_egreso(
    fields: Mapping[str, Any],
    *,
    plantel_nombre: str | None = None,
    plantel_contacto: str | None = None,
    acuerdos_clave: str | None = None,
    institucion_nombre: str | None = None,
    logo_path: str | None = None,
    plantel_obj: Any = None,
    firmante_nombre: str | None = None,
    firmante_cargo: str | None = None,
    firmante_correo: str | None = None,
    firmante_cel: str | None = None,
    firmante_firma_path: str | None = None,
    watermark_path: str | None = None,
) -> bytes:
    builder = ConstanciaEgresoBuilder(fields)
    return builder.build(
        plantel_nombre=plantel_nombre,
        plantel_contacto=plantel_contacto,
        acuerdos_clave=acuerdos_clave,
        institucion_nombre=institucion_nombre,
        logo_path=logo_path,
        plantel_obj=plantel_obj,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_correo=firmante_correo,
        firmante_cel=firmante_cel,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )


def build_constancia_finalizacion_titulacion(
    fields: Mapping[str, Any],
    *,
    plantel_nombre: str | None = None,
    plantel_contacto: str | None = None,
    acuerdos_clave: str | None = None,
    institucion_nombre: str | None = None,
    logo_path: str | None = None,
    plantel_obj: Any = None,
    firmante_nombre: str | None = None,
    firmante_cargo: str | None = None,
    firmante_correo: str | None = None,
    firmante_cel: str | None = None,
    firmante_firma_path: str | None = None,
    watermark_path: str | None = None,
) -> bytes:
    builder = ConstanciaFinalizacionTitulacionBuilder(fields)
    return builder.build(
        plantel_nombre=plantel_nombre,
        plantel_contacto=plantel_contacto,
        acuerdos_clave=acuerdos_clave,
        institucion_nombre=institucion_nombre,
        logo_path=logo_path,
        plantel_obj=plantel_obj,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_correo=firmante_correo,
        firmante_cel=firmante_cel,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )


def build_constancia_finalizacion_sin_titulacion(
    fields: Mapping[str, Any],
    *,
    plantel_nombre: str | None = None,
    plantel_contacto: str | None = None,
    acuerdos_clave: str | None = None,
    institucion_nombre: str | None = None,
    logo_path: str | None = None,
    plantel_obj: Any = None,
    firmante_nombre: str | None = None,
    firmante_cargo: str | None = None,
    firmante_correo: str | None = None,
    firmante_cel: str | None = None,
    firmante_firma_path: str | None = None,
    watermark_path: str | None = None,
) -> bytes:
    builder = ConstanciaFinalizacionSinTitulacionBuilder(fields)
    return builder.build(
        plantel_nombre=plantel_nombre,
        plantel_contacto=plantel_contacto,
        acuerdos_clave=acuerdos_clave,
        institucion_nombre=institucion_nombre,
        logo_path=logo_path,
        plantel_obj=plantel_obj,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_correo=firmante_correo,
        firmante_cel=firmante_cel,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )


def build_constancia_estudios(
    fields: Mapping[str, Any],
    *,
    plantel_nombre: str | None = None,
    plantel_contacto: str | None = None,
    acuerdos_clave: str | None = None,
    institucion_nombre: str | None = None,
    logo_path: str | None = None,
    plantel_obj: Any = None,
    firmante_nombre: str | None = None,
    firmante_cargo: str | None = None,
    firmante_correo: str | None = None,
    firmante_cel: str | None = None,
    firmante_firma_path: str | None = None,
    watermark_path: str | None = None,
) -> bytes:
    builder = ConstanciaEstudiosBuilder(fields)
    return builder.build(
        plantel_nombre=plantel_nombre,
        plantel_contacto=plantel_contacto,
        acuerdos_clave=acuerdos_clave,
        institucion_nombre=institucion_nombre,
        logo_path=logo_path,
        plantel_obj=plantel_obj,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_correo=firmante_correo,
        firmante_cel=firmante_cel,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )
