from __future__ import annotations

from typing import Any, Mapping

from uh_documentos.pdf.builders.constancia import (
    build_constancia_egreso,
    build_constancia_estudios,
    build_constancia_finalizacion_sin_titulacion,
    build_constancia_finalizacion_titulacion,
)
from uh_documentos.pdf.builders.diploma import DiplomaBuilder
from uh_documentos.pdf.builders.diploma_reconocimiento import DiplomaReconocimientoBuilder, build_diploma_reconocimiento
from uh_documentos.pdf.builders.kardex import KardexBuilder, build_kardex
from uh_documentos.pdf.builders.reconocimiento import ReconocimientoBuilder
from uh_documentos.pdf.builders.titulo import TituloBuilder, build_titulo

__all__ = [
    "try_build_reportlab",
    "KardexBuilder",
    "DiplomaBuilder",
    "ReconocimientoBuilder",
    "DiplomaReconocimientoBuilder",
    "TituloBuilder",
]


def _infer_tipo_key(fields: Mapping[str, Any]) -> str | None:
    tipo_name = (str(fields.get("tipo_documento") or fields.get("tipo_documento_nombre") or "")).strip().lower()
    if not tipo_name:
        return None
    # Título tiene maxima prioridad para no caer en builder diploma viejo
    if "titulo profesional" in tipo_name or "título profesional" in tipo_name or (
        ("titulo" in tipo_name or "título" in tipo_name)
        and ("profesional" in tipo_name or "digital" in tipo_name or "sep" in tipo_name)
    ):
        return "titulo"
    if "kardex" in tipo_name:
        return "kardex"
    if "constancia" in tipo_name and "estudio" in tipo_name:
        return "constancia_estudios"
    if "constancia" in tipo_name and "egreso" in tipo_name:
        return "constancia_egreso"
    if "finalizacion" in tipo_name and "sin proceso" in tipo_name:
        return "constancia_finalizacion_sin_titulacion"
    if "finalizacion" in tipo_name or "titulacion en proceso" in tipo_name or "título en trámite" in tipo_name:
        return "constancia_finalizacion_titulacion"
    if "diploma y reconocimiento" in tipo_name or "diploma/reconocimiento" in tipo_name:
        return "diploma_reconocimiento"
    if "diploma" in tipo_name:
        return "diploma"
    if "reconocimiento" in tipo_name:
        return "reconocimiento"
    if "titulo" in tipo_name or "título" in tipo_name:
        return "titulo"
    return None


def try_build_reportlab(
    fields: Mapping[str, Any],
    *,
    tipo_key: str | None = None,
    logo_path: str | None = None,
    plantel_obj: Any = None,
    firmante_nombre: str | None = None,
    firmante_cargo: str | None = None,
    firmante_correo: str | None = None,
    firmante_cel: str | None = None,
    firmante_firma_path: str | None = None,
    watermark_path: str | None = None,
) -> bytes | None:
    if not tipo_key:
        tipo_key = _infer_tipo_key(fields)
    if not tipo_key:
        return None

    shared = dict(
        logo_path=logo_path,
        plantel_obj=plantel_obj,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_correo=firmante_correo,
        firmante_cel=firmante_cel,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )

    if tipo_key == "kardex":
        return build_kardex(fields, **shared)
    if tipo_key == "constancia_estudios":
        return build_constancia_estudios(fields, **shared)
    if tipo_key == "constancia_egreso":
        return build_constancia_egreso(fields, **shared)
    if tipo_key == "constancia_finalizacion_titulacion":
        return build_constancia_finalizacion_titulacion(fields, **shared)
    if tipo_key == "constancia_finalizacion_sin_titulacion":
        return build_constancia_finalizacion_sin_titulacion(fields, **shared)
    if tipo_key == "diploma_reconocimiento":
        try:
            return build_diploma_reconocimiento(fields, **shared)
        except Exception:
            return None
    if tipo_key == "titulo":
        try:
            return build_titulo(fields, **shared)
        except Exception:
            return None
    if tipo_key == "diploma":
        try:
            from uh_documentos.pdf.builders.diploma import build_diploma

            return build_diploma(fields, **shared)
        except Exception:
            return None
    if tipo_key == "reconocimiento":
        try:
            from uh_documentos.pdf.builders.reconocimiento import build_reconocimiento

            return build_reconocimiento(fields, **shared)
        except Exception:
            return None
    return None
