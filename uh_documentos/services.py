from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from rest_framework.exceptions import ValidationError
from django.db import models, transaction

from uh_academico.models import Alumno, TrayectoriaAcademica
from uh_core.models import DatosContacto
from uh_documentos.document_handlers import ejecutar_handler_variables, validar_requisitos
from uh_documentos.models import DestinatarioPolimorfico, DocumentoEmitido, Externo, TipoDocumento


def generar_folio() -> str:
    return uuid.uuid4().hex[:12].upper()


def calcular_hash(*, folio: str, snapshot_datos_receptor: dict[str, Any], snapshot_academico: dict[str, Any]) -> str:
    payload = {
        "folio": folio,
        "snapshot_datos_receptor": snapshot_datos_receptor,
        "snapshot_academico": snapshot_academico,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def snapshot_alumno(alumno: Alumno) -> tuple[dict[str, Any], dict[str, Any], TrayectoriaAcademica | None]:
    trayectoria = alumno.trayectorias.filter(es_actual=True).select_related("carrera__plantel", "estatus_academico").first()
    datos = {
        "id_alumno": alumno.id,
        "matricula": alumno.matricula,
        "curp": alumno.curp,
        "nombres": alumno.nombres,
        "primer_apellido": alumno.primer_apellido,
        "segundo_apellido": alumno.segundo_apellido,
    }
    academico: dict[str, Any] = {}
    if trayectoria:
        nivel = trayectoria.nivel_actual or 1
        ciclo_nombre = getattr(trayectoria, "ciclo_nombre", None) or getattr(trayectoria.carrera.tipo_periodo, "nombre", "") or "semestral"
        academico = {
            "id_trayectoria": trayectoria.id,
            "carrera": trayectoria.carrera.nombre,
            "id_carrera": trayectoria.carrera_id,
            "plantel": trayectoria.carrera.plantel.nombre,
            "id_plantel": trayectoria.carrera.plantel_id,
            "estatus_academico": trayectoria.estatus_academico.nombre,
            "id_estatus_academico": trayectoria.estatus_academico_id,
            "nivel_actual": trayectoria.nivel_actual,
            "nivel_actual_ordinal": f"{nivel}°",
            "ciclo_nombre": ciclo_nombre,
            "promedio_general": str(trayectoria.promedio_general) if trayectoria.promedio_general is not None else None,
            "creditos_acumulados": str(trayectoria.creditos_acumulados) if trayectoria.creditos_acumulados is not None else None,
        }
        try:
            from uh_academico.models import InscripcionPeriodo
            inscripcion_actual = InscripcionPeriodo.objects.filter(
                trayectoria_academica_id=trayectoria.id,
                es_actual=True,
            ).select_related("periodo_academico__ciclo_escolar").first()
            if inscripcion_actual and inscripcion_actual.periodo_academico:
                periodo = inscripcion_actual.periodo_academico
                ciclo = periodo.ciclo_escolar
                academico["ciclo_escolar_clave"] = getattr(ciclo, "clave", "") or ""
                academico["periodo_nombre"] = getattr(periodo, "clave", "") or ""
                if periodo.fecha_inicio:
                    academico["periodo_fecha_inicio"] = periodo.fecha_inicio.strftime("%d/%m/%Y")
                if periodo.fecha_fin:
                    academico["periodo_fecha_fin"] = periodo.fecha_fin.strftime("%d/%m/%Y")
        except Exception:
            pass
    return datos, academico, trayectoria


def snapshot_externo(externo: Externo) -> tuple[dict[str, Any], dict[str, Any]]:
    contacto = externo.contacto
    datos = {
        "id_externo": externo.id,
        "nombres": externo.nombres,
        "primer_apellido": externo.primer_apellido,
        "segundo_apellido": externo.segundo_apellido,
        "correo_electronico": getattr(contacto, "correo_electronico", ""),
        "telefono": getattr(contacto, "telefono", ""),
        "celular": getattr(contacto, "celular", ""),
    }
    return datos, {}


def validar_reglas(
    *,
    tipo_documento: TipoDocumento,
    trayectoria: TrayectoriaAcademica | None,
    aprobado_directiva: bool,
    extra: dict[str, Any] | None = None,
) -> None:
    validar_requisitos(
        tipo_documento=tipo_documento,
        trayectoria=trayectoria,
        aprobado_directiva=aprobado_directiva,
        extra=extra or {},
    )


@transaction.atomic
def crear_documento(
    *,
    tipo_documento: TipoDocumento,
    plantel_id: int,
    autoridad_id: int | None,
    alumno_id: int | None,
    externo_payload: dict[str, Any] | None,
    aprobado_directiva: bool = True,
    archivo: Any | None = None,
    extra: dict[str, Any] | None = None,
) -> DocumentoEmitido:
    alumno = None
    externo = None
    snapshot_datos_receptor: dict[str, Any]
    snapshot_academico: dict[str, Any]
    trayectoria = None
    extra = extra or {}

    if alumno_id:
        alumno = Alumno.objects.select_related("domicilio", "contacto").get(pk=alumno_id)
        snapshot_datos_receptor, snapshot_academico, trayectoria = snapshot_alumno(alumno)
        destinatario = DestinatarioPolimorfico.objects.create(entidad_tipo="alumno", entidad_id=alumno.id)
    elif externo_payload:
        contacto = DatosContacto.objects.create(
            telefono=externo_payload.get("telefono", "") or "",
            celular=externo_payload.get("celular", "") or "",
            correo_electronico=externo_payload.get("correo", "") or "",
        )
        externo = Externo.objects.create(
            nombres=externo_payload.get("nombres", "") or "",
            primer_apellido=externo_payload.get("apellidos", "") or "",
            segundo_apellido="",
            contacto=contacto,
        )
        snapshot_datos_receptor, snapshot_academico = snapshot_externo(externo)
        destinatario = DestinatarioPolimorfico.objects.create(entidad_tipo="externo", entidad_id=externo.id)
    else:
        raise ValidationError("Se requiere alumno_id o datos de externo.")

    if extra:
        merged_extra = dict(snapshot_academico)
        merged_extra.update({k: v for k, v in extra.items() if v is not None})
        snapshot_academico = merged_extra

    # --- Reglas específicas de TÍTULO ---
    _cat = (getattr(tipo_documento, "categoria", "") or "").upper()
    _nom = (getattr(tipo_documento, "nombre", "") or "").upper()
    _es_titulo = (
        _cat == "TITULO"
        or "TÍTULO" in _nom
        or "TITULO" in _nom
    )
    if _es_titulo:
        if not alumno:
            raise ValidationError("Los Títulos profesionales sólo pueden emitirse a alumnos.")
        folio_sep = (extra.get("folio_sep") or "").strip()
        if not folio_sep:
            raise ValidationError("El Título requiere el folio SEP ingresado manualmente.")
        # -- Estatus "Titulado" requerido --
        trayectorias = TrayectoriaAcademica.objects.filter(alumno_id=alumno.id).select_related(
            "estatus_academico"
        )
        es_titulado = False
        for t in trayectorias:
            nombre_estatus = (getattr(getattr(t, "estatus_academico", None), "nombre", "") or "").upper()
            if "TITULADO" in nombre_estatus or "GRADUADO" in nombre_estatus:
                es_titulado = True
                break
        if not es_titulado:
            raise ValidationError(
                "El alumno no tiene estatus académico 'Titulado' en ninguna de sus trayectorias. "
                "No es posible expedir un Título Profesional."
            )
        # -- Unico por alumno (cualquier tipo Título) --
        ya_tiene = DocumentoEmitido.objects.filter(alumno_id=alumno.id).filter(
            models.Q(tipo_documento__categoria__iexact="TITULO")
            | models.Q(tipo_documento__nombre__iregex=r"t[ií]tulo")
        ).exists()
        if ya_tiene:
            raise ValidationError(
                "Este alumno ya tiene un Título Profesional emitido. Sólo se permite un Título por persona."
            )

    validar_reglas(
        tipo_documento=tipo_documento,
        trayectoria=trayectoria,
        aprobado_directiva=aprobado_directiva,
        extra=extra,
    )

    for _ in range(5):
        folio = generar_folio()
        if not DocumentoEmitido.objects.filter(folio=folio).exists():
            break
    else:
        raise ValidationError("No fue posible generar un folio único.")

    hash_documento = calcular_hash(
        folio=folio,
        snapshot_datos_receptor=snapshot_datos_receptor,
        snapshot_academico=snapshot_academico,
    )

    doc = DocumentoEmitido.objects.create(
        folio=folio,
        tipo_documento=tipo_documento,
        plantel_id=plantel_id,
        autoridad_id=autoridad_id,
        destinatario=destinatario,
        alumno=alumno,
        externo=externo,
        hash_documento=hash_documento,
        snapshot_datos_receptor=snapshot_datos_receptor,
        snapshot_academico=snapshot_academico,
        archivo=archivo,
    )
    handler_campos, handler_repeticiones = ejecutar_handler_variables(
        tipo_documento=tipo_documento,
        trayectoria=trayectoria,
        aprobado_directiva=aprobado_directiva,
        extra=extra,
    )
    if handler_campos:
        merged = dict(snapshot_academico)
        merged.update(handler_campos)
        if doc.snapshot_academico != merged:
            doc.snapshot_academico = merged
            doc.save(update_fields=["snapshot_academico"])
    return doc
