from __future__ import annotations

from typing import Any, Mapping

from uh_documentos.pdf.builders.base_builder import BaseDocumentBuilder


class ReconocimientoBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "RECONOCIMIENTO"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Reconocimiento")

    def body_segments(self) -> list[tuple[str, bool]]:
        nombre = str(self.fields.get("nombre") or self.fields.get("nombre_completo") or "")
        motivo = str(self.fields.get("motivo_reconocimiento") or self.fields.get("motivo") or "su destacada participación y compromiso")
        texto = (
            f"La <b>{self.fields.get('institucion_nombre', 'Colegio Universitario Hispana')}</b> "
            f"otorga el presente <b>RECONOCIMIENTO</b> a <b>{nombre}</b>, "
            f"por {motivo}."
        )
        return [(texto, True)]

    def datos_rows(self) -> list[tuple[str, str]]:
        return []


def build_reconocimiento(
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
    builder = ReconocimientoBuilder(fields)
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
