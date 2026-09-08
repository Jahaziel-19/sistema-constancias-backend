from __future__ import annotations

from typing import Any, Mapping

from uh_documentos.pdf.builders.base_builder import BaseDocumentBuilder


class DiplomaBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "DIPLOMA"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Diploma")

    def body_segments(self) -> list[tuple[str, bool]]:
        nombre = str(self.fields.get("nombre") or self.fields.get("nombre_completo") or "")
        carrera = str(self.fields.get("carrera_nombre") or self.fields.get("carrera") or "")
        titulo = str(self.fields.get("titulo_otorgado") or f"Titulado(a) en {carrera}" if carrera else "Titulado(a)")
        periodo = str(self.fields.get("periodo_nombre") or "")
        promedio = str(self.fields.get("promedio_general") or "")
        turno = str(self.fields.get("turno") or "")
        modalidad = str(self.fields.get("modalidad") or "")
        texto = (
            f"Por este medio se otorga el presente <b>DIPLOMA</b> a <b>{nombre}</b>, "
            f"por haber concluido satisfactoriamente los estudios de <b>{carrera}</b>, "
            f"obteniendo el título de <b>{titulo}</b>."
        )
        if periodo:
            texto += f"<br/><br/>Periodo: {periodo}"
        if promedio:
            texto += f"<br/>Promedio: {promedio}"
        if turno:
            texto += f"<br/>Turno: {turno}"
        if modalidad:
            texto += f"<br/>Modalidad: {modalidad}"
        return [(texto, True)]

    def datos_rows(self) -> list[tuple[str, str]]:
        return []


def build_diploma(
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
    builder = DiplomaBuilder(fields)
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
