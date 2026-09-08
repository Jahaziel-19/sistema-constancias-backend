from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.utils import timezone


NUMEROS_ENTEROS = [
    "Cero", "Uno", "Dos", "Tres", "Cuatro", "Cinco", "Seis", "Siete", "Ocho", "Nueve",
    "Diez", "Once", "Doce", "Trece", "Catorce", "Quince", "Dieciséis", "Diecisiete",
    "Dieciocho", "Diecinueve", "Veinte",
]
DECENAS = [
    "", "", "Veinti", "Treinta", "Cuarenta", "Cincuenta", "Sesenta", "Setenta",
    "Ochenta", "Noventa", "Cien",
]
FRACCIONES_UNIDAD = {
    "0": "",
    "1": "Un Décimo",
    "2": "Dos Décimos",
    "3": "Tres Décimos",
    "4": "Cuatro Décimos",
    "5": "Cinco Décimos",
    "6": "Seis Décimos",
    "7": "Siete Décimos",
    "8": "Ocho Décimos",
    "9": "Nueve Décimos",
}


def _numero_a_letras(n: int) -> str:
    if 0 <= n <= 20:
        return NUMEROS_ENTEROS[n]
    if n < 100:
        decena = n // 10
        unidad = n % 10
        base = DECENAS[decena]
        if decena == 10:
            return base
        if decena == 2 and unidad > 0:
            return base + NUMEROS_ENTEROS[unidad].lower()
        if unidad == 0:
            return base
        return f"{base} y {NUMEROS_ENTEROS[unidad].lower()}"
    if n < 1000:
        centena = n // 100
        resto = n % 100
        prefix = {
            1: "Ciento" if resto else "Cien",
            2: "Doscientos", 3: "Trescientos", 4: "Cuatrocientos",
            5: "Quinientos", 6: "Seiscientos", 7: "Setecientos",
            8: "Ochocientos", 9: "Novecientos",
        }[centena]
        if resto == 0:
            return prefix
        return f"{prefix} {_numero_a_letras(resto).lower()}"
    if n < 1_000_000:
        millar = n // 1000
        resto = n % 1000
        if millar == 1:
            prefix = "Mil"
        else:
            prefix = f"{_numero_a_letras(millar).capitalize()} mil"
        if resto == 0:
            return prefix
        return f"{prefix} {_numero_a_letras(resto).lower()}"
    return str(n)


def numero_en_letras(valor: Any) -> str:
    if valor is None:
        return ""
    try:
        n = int(float(valor))
    except Exception:
        return ""
    if n == 0:
        return "Cero"
    return _numero_a_letras(n)


def fecha_larga(d: Any) -> str:
    if not d:
        return ""
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        return f"{d.day} de {meses[d.month - 1]} de {d.year}"
    return str(d)


def lugar_fecha(*, municipio: str, estado: str, dt: Any, default: str = "") -> str:
    parts = []
    if municipio:
        parts.append(municipio)
    if estado:
        parts.append(estado)
    loc = ", ".join(parts) if parts else ""
    if loc and isinstance(dt, (datetime, date)):
        if isinstance(dt, datetime):
            dt = dt.date()
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        return f"{loc}, a {dt.day} de {meses[dt.month - 1]} de {dt.year}"
    if default:
        if isinstance(dt, (datetime, date)):
            if isinstance(dt, datetime):
                dt = dt.date()
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            ]
            return f"{default}, a {dt.day} de {meses[dt.month - 1]} de {dt.year}"
        return default
    if isinstance(dt, (datetime, date)):
        if isinstance(dt, datetime):
            dt = dt.date()
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        return f"a {dt.day} de {meses[dt.month - 1]} de {dt.year}"
    return ""


def merge_field_maps(*maps: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m in maps:
        if not m:
            continue
        for k, v in m.items():
            if k not in out:
                out[k] = v
    return out


@dataclass
class RenderContext:
    fields: dict[str, Any]
    repeats: dict[str, list[dict[str, Any]]]


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, Decimal):
        s = f"{v:.1f}"
    elif isinstance(v, float):
        s = f"{v:.1f}"
    else:
        s = str(v)
    if not s:
        return "—"
    return s


def ordinal_nivel(n: Any) -> str:
    try:
        n = int(n)
    except Exception:
        return ""
    if n <= 0:
        return ""
    suf = {1: "er", 2: "do", 3: "er"}.get(n, "°")
    return f"{n}{suf}"


def build_render_context(
    documento,
    *,
    extra_campos: dict[str, Any] | None = None,
    extra_repeticiones: dict[str, list[dict[str, Any]]] | None = None,
    plantel=None,
    autoridad=None,
    alumno=None,
    trayectoria=None,
    externo=None,
    kardex_preload: dict[str, Any] | None = None,
) -> RenderContext:
    tipo = documento.tipo_documento
    plantel = plantel or documento.plantel
    autoridad = autoridad or documento.autoridad
    alumno = alumno or documento.alumno
    externo = externo or documento.externo
    if trayectoria is None and alumno:
        try:
            trayectoria = alumno.trayectorias.filter(es_actual=True).select_related(
                "carrera__plantel", "carrera__tipo_periodo", "estatus_academico"
            ).first()
        except Exception:
            trayectoria = None

    now = timezone.localtime(timezone.now())

    carrera = trayectoria.carrera if trayectoria else None
    dom_plantel = plantel.domicilio if plantel and hasattr(plantel, "domicilio") else None
    contacto_plantel = plantel.contacto if plantel and hasattr(plantel, "contacto") else None
    contacto_autoridad = autoridad.contacto if autoridad and hasattr(autoridad, "contacto") else None

    direccion_plantel = ""
    if dom_plantel:
        partes = []
        if dom_plantel.calle or dom_plantel.numero_exterior:
            partes.append(f"{dom_plantel.calle} {dom_plantel.numero_exterior}".strip())
            if dom_plantel.numero_interior:
                partes[-1] = f"{partes[-1]} Int. {dom_plantel.numero_interior}".strip()
        if dom_plantel.colonia:
            partes.append(dom_plantel.colonia)
        cp = dom_plantel.codigo_postal.strip()
        ciudad = ", ".join([x for x in [dom_plantel.municipio, dom_plantel.estado] if x])
        tail = " ".join([x for x in [cp and f"C.P. {cp}", ciudad] if x]).strip()
        if tail:
            partes.append(tail)
        direccion_plantel = ", ".join([p for p in partes if p])

    nombre_receptor = ""
    if alumno:
        nombre_receptor = " ".join([
            alumno.nombres or "",
            alumno.primer_apellido or "",
            alumno.segundo_apellido or "",
        ]).strip()
    elif externo:
        nombre_receptor = " ".join([
            externo.nombres or "",
            externo.primer_apellido or "",
            externo.segundo_apellido or "",
        ]).strip()

    periodo_nombre = ""
    periodo = None
    if trayectoria and carrera:
        try:
            periodo_nombre = getattr(carrera.tipo_periodo, "nombre", "") or ""
            if periodo_nombre:
                periodo = carrera.tipo_periodo
            elif getattr(carrera, "tipo_periodo_id", None):
                from uh_academico.models import TipoPeriodo
                periodo = TipoPeriodo.objects.filter(pk=carrera.tipo_periodo_id).first()
                periodo_nombre = (periodo.nombre or "") if periodo else ""
        except Exception:
            pass

    periodo_academico_actual = None
    ciclo_escolar_actual = None
    if trayectoria and trayectoria.id:
        try:
            from uh_academico.models import InscripcionPeriodo
            inscripcion_actual = InscripcionPeriodo.objects.filter(
                trayectoria_academica_id=trayectoria.id,
                es_actual=True,
            ).select_related("periodo_academico__ciclo_escolar").first()
            if inscripcion_actual and inscripcion_actual.periodo_academico:
                periodo_academico_actual = inscripcion_actual.periodo_academico
                ciclo_escolar_actual = periodo_academico_actual.ciclo_escolar
        except Exception:
            pass

    if periodo_academico_actual and getattr(periodo_academico_actual, "clave", ""):
        periodo_nombre = periodo_academico_actual.clave

    avance = ""
    if trayectoria and carrera and carrera.total_ciclos:
        try:
            pct = min(100, max(0, int(round((trayectoria.nivel_actual or 0) * 100 / carrera.total_ciclos))))
            avance = f"{pct}%"
        except Exception:
            avance = ""

    nombre_autoridad = ""
    cargo_autoridad = ""
    if autoridad:
        nombre_autoridad = " ".join([autoridad.nombres or "", autoridad.apellidos or ""]).strip()
        cargo_autoridad = autoridad.cargo or ""

    nivel_actual_ordinal = ""
    if trayectoria and trayectoria.nivel_actual:
        try:
            n = int(trayectoria.nivel_actual)
        except Exception:
            n = 0
        if n:
            nivel_actual_ordinal = f"{n}°"

    periodos_items: list[dict[str, Any]] = []
    materias_items: list[dict[str, Any]] = []
    total_creditos = 0
    total_materias = 0
    promedio = None
    kardex_preload = kardex_preload or {}
    if not kardex_preload and alumno:
        try:
            from uh_academico.models import CalificacionDetalle, InscripcionPeriodo, Materia, PlanEstudio
            plan = None
            if trayectoria and trayectoria.carrera_id:
                plan = (
                    PlanEstudio.objects
                    .filter(carrera_id=trayectoria.carrera_id)
                    .order_by("-vigencia_inicio", "-version", "-id")
                    .first()
                )
            materias_qs = []
            if plan:
                materias_qs = list(
                    Materia.objects
                    .filter(plan_estudio_id=plan.id)
                    .order_by("ciclo_numero", "clave_materia")
                )
            califs = []
            if materias_qs:
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
            calif_por_materia: dict[int, dict[str, Any]] = {}
            suma_final = 0.0
            count_final = 0
            for det in califs:
                mat = det.catalogo_materia
                final = det.calificacion_final
                if isinstance(final, (int, float, Decimal)):
                    suma_final += float(final)
                    count_final += 1
                creditos = int(mat.creditos or 0) if mat else 0
                calif_por_materia[mat.id] = {
                    "creditos": creditos,
                    "materia": mat.nombre_materia or "",
                    "clave": mat.clave_materia or "",
                    "ordinario": _fmt(det.calificacion_ordinaria),
                    "extra_1": _fmt(det.extraordinario_1),
                    "extra_2": _fmt(det.extraordinario_2),
                    "final": _fmt(det.calificacion_final),
                    "calificacion_letra": det.calificacion_letra or numero_en_letras(det.calificacion_final),
                }
            last_ciclo = None
            periodo_label = periodo_nombre.replace("Semestral", "Semestre").replace("Cuatrimestral", "Cuatrimestre")
            if not periodo_label:
                periodo_label = "Periodo"
            for mat in materias_qs:
                c = calif_por_materia.get(mat.id)
                if not c:
                    creditos = int(mat.creditos or 0)
                    c = {
                        "creditos": creditos,
                        "materia": mat.nombre_materia or "",
                        "clave": mat.clave_materia or "",
                        "ordinario": "—",
                        "extra_1": "—",
                        "extra_2": "—",
                        "final": "—",
                        "calificacion_letra": "—",
                    }
                ciclo = mat.ciclo_numero
                if ciclo != last_ciclo:
                    periodos_items.append({
                        "_periodo_label": f"{ordinal_nivel(ciclo)} {periodo_label}",
                    })
                    last_ciclo = ciclo
                total_creditos += c["creditos"]
                total_materias += 1
                materias_items.append({
                    "creditos": c["creditos"],
                    "materia": c["materia"],
                    "clave": c["clave"],
                    "ordinario": c["ordinario"],
                    "extra_1": c["extra_1"],
                    "extra_2": c["extra_2"],
                    "final": c["final"],
                    "calificacion_letra": c["calificacion_letra"],
                })
            if count_final:
                promedio = round(suma_final / count_final, 2)
        except Exception:
            pass
    elif kardex_preload:
        materias_items = kardex_preload.get("materias_items", [])
        periodos_items = kardex_preload.get("periodos_items", [])
        total_creditos = kardex_preload.get("total_creditos", 0)
        total_materias = kardex_preload.get("total_materias", 0)
        promedio = kardex_preload.get("promedio")

    if not promedio and trayectoria and trayectoria.promedio_general is not None:
        promedio = float(trayectoria.promedio_general)

    if trayectoria and trayectoria.creditos_acumulados is not None and total_creditos == 0:
        total_creditos = int(trayectoria.creditos_acumulados)

    try:
        from uh_core.models import ConfiguracionInstitucional
        cfg = ConfiguracionInstitucional.objects.first()
        institucion_nombre = cfg.nombre_institucion if cfg else "Colegio Universitario Hispana"
    except Exception:
        institucion_nombre = getattr(settings, "INSTITUCION_NOMBRE", "Colegio Universitario Hispana")

    snapshot_datos_receptor = documento.snapshot_datos_receptor or {}
    snapshot_academico = documento.snapshot_academico or {}

    fields = {
        "folio": documento.folio,
        "folio_verif": documento.folio,
        "fecha_emision": fecha_larga(now),
        "fecha_hora_emision": fecha_larga(now),
        "hash_documento": documento.hash_documento,
        "tipo_documento": tipo.nombre if tipo else "",
        "institucion": institucion_nombre,
        "institucion_nombre": institucion_nombre,
        "plantel": plantel.nombre if plantel else "",
        "clave_plantel": plantel.clave_plantel if plantel else "",
        "reg_sep": plantel.rgp if plantel else "",
        "reg_profesiones": plantel.rgp if plantel else "",
        "acuerdos_sep": carrera.acuerdo_sep if carrera and carrera.acuerdo_sep else "",
        "direccion_plantel": direccion_plantel,
        "telefono_plantel": getattr(contacto_plantel, "telefono", "") or "",
        "correo_plantel": getattr(contacto_plantel, "correo_electronico", "") or "",
        "web_plantel": plantel.pagina_web if plantel else "",
        "municipio_plantel": getattr(dom_plantel, "municipio", "") or "",
        "estado_plantel": getattr(dom_plantel, "estado", "") or "",
        "lugar_fecha": lugar_fecha(
            municipio=str(plantel.nombre) if plantel and plantel.nombre else "",
            estado="",
            dt=now,
            default=str(plantel.nombre) if plantel and plantel.nombre else "Huauchinango",
        ),

        "nombre_completo": nombre_receptor,
        "nombres": snapshot_datos_receptor.get("nombres") or "",
        "primer_apellido": snapshot_datos_receptor.get("primer_apellido") or "",
        "segundo_apellido": snapshot_datos_receptor.get("segundo_apellido") or "",
        "ap_paterno": snapshot_datos_receptor.get("primer_apellido") or "",
        "ap_materno": snapshot_datos_receptor.get("segundo_apellido") or "",
        "matricula": snapshot_datos_receptor.get("matricula") or "",
        "curp": snapshot_datos_receptor.get("curp") or "",

        "carrera": snapshot_academico.get("carrera") or (carrera.nombre if carrera else ""),
        "id_carrera": snapshot_academico.get("id_carrera") or (carrera.id if carrera else ""),
        "plantel_academico": snapshot_academico.get("plantel") or (plantel.nombre if plantel else ""),
        "estatus_academico": snapshot_academico.get("estatus_academico") or "",
        "nivel_actual": trayectoria.nivel_actual if trayectoria else "",
        "nivel_actual_ordinal": nivel_actual_ordinal,
        "cuatrimestre": nivel_actual_ordinal,
        "semestre": nivel_actual_ordinal,
        "promedio_general": f"{promedio:.2f}" if promedio is not None else (
            snapshot_academico.get("promedio_general") or ""
        ),
        "promedio": f"{promedio:.2f}" if promedio is not None else "",
        "promedio_letras": numero_en_letras(promedio) if promedio is not None else "",
        "creditos_acumulados": total_creditos or (
            snapshot_academico.get("creditos_acumulados") or ""
        ),
        "creditos": total_creditos or (snapshot_academico.get("creditos_acumulados") or ""),
        "total_materias": total_materias or "",
        "avance": avance,
        "avance_plan": avance,
        "periodo": periodo_nombre,
        "turno": snapshot_academico.get("turno") or (trayectoria.turno if trayectoria and hasattr(trayectoria, "turno") and trayectoria.turno else "") or "Escolarizado",
        "modalidad": snapshot_academico.get("modalidad") or (trayectoria.modalidad if trayectoria and hasattr(trayectoria, "modalidad") and trayectoria.modalidad else "") or "Escolarizada",
        "area_emisora": tipo.nombre if tipo else "",
        "periodo_academico_nombre": periodo_nombre,
        "periodo_academico_tipo": (getattr(periodo, "nombre", "") or "").lower(),
        "kardex_periodo_label": (
            "Cuatrimestre"
            if periodo and getattr(periodo, "nombre", "").lower() in ("cuatrimestral", "cuatrimestral")
            else "Semestre"
            if periodo and getattr(periodo, "nombre", "").lower() in ("semestral", "semestral")
            else "Nivel"
        ),
        "plan_vigencia": (
            f"{plan.vigencia_inicio.strftime('%Y')}-{plan.vigencia_fin.strftime('%Y')}"
            if plan and getattr(plan, "vigencia_inicio", None) and getattr(plan, "vigencia_fin", None)
            else (plan.vigencia_inicio.strftime("%Y") if plan and getattr(plan, "vigencia_inicio", None) else "")
        ),
        "periodo_nombre": snapshot_academico.get("periodo_nombre") or periodo_nombre or "",
        "ciclo_escolar_clave": getattr(ciclo_escolar_actual, "clave", "") or "",
        "periodo_fecha_inicio": periodo_academico_actual.fecha_inicio.strftime("%d/%m/%Y") if periodo_academico_actual and periodo_academico_actual.fecha_inicio else "",
        "periodo_fecha_fin": periodo_academico_actual.fecha_fin.strftime("%d/%m/%Y") if periodo_academico_actual and periodo_academico_actual.fecha_fin else "",

        "firmante": nombre_autoridad,
        "cargo_firmante": cargo_autoridad,
        "cargo_firmante_texto": cargo_autoridad,
        "correo_firmante": getattr(contacto_autoridad, "correo_electronico", "") or "",
        "cel_firmante": getattr(contacto_autoridad, "celular", "") or "",
        "tel_firmante": getattr(contacto_autoridad, "telefono", "") or "",

        "snapshot_receptor": snapshot_datos_receptor,
        "snapshot_academico": snapshot_academico,
    }

    repeats = {
        "periodos": periodos_items,
        "materias": materias_items,
    }

    for k, v in (snapshot_datos_receptor or {}).items():
        if k not in fields:
            fields[k] = v
    for k, v in (snapshot_academico or {}).items():
        if k not in fields:
            fields[k] = v

    if extra_campos:
        fields = merge_field_maps(fields, extra_campos)
    if extra_repeticiones:
        merged_repeats: dict[str, list[dict[str, Any]]] = {k: list(v) for k, v in repeats.items()}
        for k, v in extra_repeticiones.items():
            if k in merged_repeats:
                merged_repeats[k] = list(merged_repeats[k]) + list(v)
            else:
                merged_repeats[k] = list(v)
        repeats = merged_repeats

    return RenderContext(fields=fields, repeats=repeats)
