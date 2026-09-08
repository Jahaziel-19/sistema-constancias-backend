from __future__ import annotations

import io
from typing import Any, Mapping

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from uh_documentos.pdf.builders.base_builder import BaseDocumentBuilder
from uh_documentos.pdf.components.base import GOLD, NAVY, PageGeometry, RLComponents


def _kardex_body(fields: Mapping[str, Any]) -> list[tuple[str, bool]]:
    parts: list[tuple[str, bool]] = []
    nombre = str(fields.get("nombre") or "Nombre Completo del Estudiante")
    carrera = str(fields.get("carrera") or fields.get("carrera_nombre") or "")
    plantel = str(fields.get("plantel_nombre") or "")
    promedio = str(fields.get("promedio_general") or "")
    estatus = str(fields.get("estatus_academico") or "")
    parts.append(("A QUIEN CORRESPONDA:", True))
    parts.append(("\n\n", False))
    parts.append(("Por medio del presente se hace constar el Kardex Oficial de calificaciones de ", False))
    parts.append((nombre, True))
    if carrera:
        parts.append((" de la carrera de ", False))
        parts.append((carrera, True))
    if plantel:
        parts.append((" del plantel ", False))
        parts.append((plantel, True))
    if estatus:
        parts.append((", con estatus académico ", False))
        parts.append((estatus, True))
    if promedio:
        parts.append((". Con promedio general de ", False))
        parts.append((promedio, True))
    parts.append((":", False))
    return parts


def _kardex_datos_rows(fields: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    nombre = str(fields.get("nombre") or "")
    if nombre:
        rows.append(("Nombre completo", nombre))
    carrera = str(fields.get("carrera") or fields.get("carrera_nombre") or "")
    if carrera:
        rows.append(("Carrera", carrera))
    matricula = str(fields.get("matricula") or "")
    if matricula:
        rows.append(("Matrícula", matricula))
    periodo = str(fields.get("periodo_nombre") or fields.get("plan_vigencia") or "")
    if periodo:
        rows.append(("Periodo / Plan", periodo))
    nivel = str(fields.get("nivel_actual_ordinal") or fields.get("nivel_actual") or "")
    if nivel:
        rows.append(("Nivel actual", nivel))
    promedio = str(fields.get("promedio_general") or "")
    if promedio:
        rows.append(("Promedio general", promedio))
    creditos = str(fields.get("creditos_acumulados") or fields.get("creditos") or "")
    if creditos:
        rows.append(("Créditos acumulados", creditos))
    return rows


def build_kardex(
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
    builder = KardexBuilder(fields)
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


class KardexBuilder(BaseDocumentBuilder):
    def side_label(self) -> str:
        return "KARDEX GENERAL"

    def titulo(self) -> str:
        return str(self.fields.get("tipo_documento") or "Kardex General")

    def body_segments(self) -> list[tuple[str, bool]]:
        return _kardex_body(self.fields)

    def datos_rows(self) -> list[tuple[str, str]]:
        return _kardex_datos_rows(self.fields)

    @staticmethod
    def _group_items_by_nivel(items: list[dict[str, Any]]) -> list[tuple[Any, list[dict[str, Any]]]]:
        niveles: list[tuple[Any, list[dict[str, Any]]]] = []
        current_nivel = None
        current_items: list[dict[str, Any]] = []
        for mat in items:
            nivel = mat.get("ciclo_numero")
            if nivel != current_nivel:
                if current_items:
                    niveles.append((current_nivel, current_items))
                current_nivel = nivel
                current_items = [mat]
            else:
                current_items.append(mat)
        if current_items:
            niveles.append((current_nivel, current_items))
        return niveles

    def build(self, *, plantel_nombre: str | None = None, plantel_contacto: str | None = None, acuerdos_clave: str | None = None, institucion_nombre: str | None = None, logo_path: str | None = None, plantel_obj: Any = None, firmante_nombre: str | None = None, firmante_cargo: str | None = None, firmante_correo: str | None = None, firmante_cel: str | None = None, firmante_firma_path: str | None = None, watermark_path: str | None = None) -> bytes:
        buf = io.BytesIO()
        w, h = LETTER
        geom = PageGeometry(width=w, height=h, margin_x=26, margin_y=26)

        plantel = plantel_nombre or self._plantel_nombre()
        contacto = plantel_contacto or self._plantel_contacto()
        institucion = institucion_nombre or self._institucion_nombre()
        acuerdos = acuerdos_clave or str(self.fields.get("acuerdos_clave") or "")

        institucion_clave = ""
        registro_sep = ""
        if plantel_obj is not None:
            try:
                institucion_clave = str(getattr(plantel_obj, "rgp", "") or getattr(plantel_obj, "clave_plantel", "") or "")
                registro_sep = str(getattr(plantel_obj, "registro_sep", "") or "")
            except Exception:
                institucion_clave = ""
                registro_sep = ""
        else:
            institucion_clave = str(self.fields.get("institucion_clave") or "")
            registro_sep = str(self.fields.get("registro_sep") or "")

        if not watermark_path:
            try:
                from django.conf import settings
                from pathlib import Path
                base = Path(settings.MEDIA_ROOT)
                for candidate in [
                    base / "watemark" / "marca_agua.png",
                    base / "watermark" / "marca_agua.png",
                ]:
                    if candidate.exists():
                        watermark_path = str(candidate)
                        break
            except Exception:
                pass

        materias: list[dict[str, Any]] = list(self.fields.get("materias_items") or [])
        side_label_text = str(self.fields.get("side_label") or self.fields.get("area_emisora") or self.side_label())

        if "promedio_general" not in self.fields or "creditos_acumulados" not in self.fields:
            try:
                finals = []
                credits = 0.0
                for m in materias:
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
                if finals and "promedio_general" not in self.fields:
                    self.fields["promedio_general"] = round(sum(finals) / len(finals), 2)
                if credits and "creditos_acumulados" not in self.fields:
                    self.fields["creditos_acumulados"] = int(credits) if credits == int(credits) else round(credits, 2)
            except Exception:
                pass

        # ---- 1. Calcular alturas fijas --------------------------------------------------
        HEADER_ROW_H = 15
        NIVEL_H = 14
        ROW_H = 15
        TABLA_BOTTOM_PAD = 10

        # Footer reservation (solo usada en la ÚLTIMA página)
        FOOTER_BLOCK_H = -30  # espacio reservado desde content_y hacia arriba (reducir para aprovechar más espacio)

        # Helper para medir bloques de materias (altura acumulada en una lista de items)
        def _chunk_height(items_in_chunk: list[dict[str, Any]]) -> float:
            levels = self._group_items_by_nivel(items_in_chunk)
            total = HEADER_ROW_H
            for _, its in levels:
                total += NIVEL_H + (len(its) * ROW_H)
            return total

        # ---- 2. Calcular posición inicial para el chunk 1 (después de intro completo) ---
        dummy_c = canvas.Canvas(io.BytesIO(), pagesize=LETTER)
        dummy_comp = RLComponents(dummy_c, geom=geom, fields=self.fields)

        dummy_comp.draw_double_border()
        dummy_comp.draw_header(
            plantel_nombre=plantel,
            institucion_nombre=institucion,
            logo_path=logo_path,
            tipo_documento=None,
            folio=None,
            institucion_clave=institucion_clave or None,
            registro_sep=registro_sep or None,
        )
        dummy_comp.draw_lugar_fecha()
        dummy_comp.draw_titulo(self.titulo())   
        body_bottom = dummy_comp.draw_paragraph_with_marcas(self.body_segments())
        tabla_y_top_1 = body_bottom - 22
        after_datos = dummy_comp.draw_tabla_datos(self.datos_rows(), y_top=tabla_y_top_1)
        FIRST_TABLE_TOP = after_datos - 18
        FIRST_BOTTOM_LIMIT = dummy_comp.content_y - 30 #FOOTER_BLOCK_H

        # ---- 3. Chunking: primera página + páginas siguientes (tabla empieza arriba) ----
        chunks: list[list[dict[str, Any]]] = []
        remaining = list(materias)

        if remaining:
            # Página 1
            available_h = FIRST_TABLE_TOP - FIRST_BOTTOM_LIMIT - HEADER_ROW_H - TABLA_BOTTOM_PAD
            chunk1: list[dict[str, Any]] = []
            for m in remaining:
                trial = chunk1 + [m]
                if _chunk_height(trial) <= available_h or not chunk1:
                    chunk1.append(m)
                else:
                    break
            chunks.append(chunk1)
            remaining = remaining[len(chunk1):]

            # Páginas 2..N (continuation)
            NEXT_TABLE_TOP = dummy_comp.content_y + dummy_comp.content_h - 40
            NEXT_BOTTOM_LIMIT = dummy_comp.content_y - 40 #FOOTER_BLOCK_H
            NEXT_AVAILABLE = NEXT_TABLE_TOP - NEXT_BOTTOM_LIMIT - HEADER_ROW_H - TABLA_BOTTOM_PAD - 18
            while remaining:
                chunk: list[dict[str, Any]] = []
                for m in remaining:
                    trial = chunk + [m]
                    if _chunk_height(trial) <= NEXT_AVAILABLE or not chunk:
                        chunk.append(m)
                    else:
                        break
                chunks.append(chunk)
                remaining = remaining[len(chunk):]

        if not chunks:
            chunks = [[]]

        # ---- 4. Render páginas reales ---------------------------------------------------
        c = canvas.Canvas(buf, pagesize=LETTER)
        total_pages = len(chunks)
        for page_idx, chunk in enumerate(chunks):
            is_first = page_idx == 0
            is_last = page_idx == total_pages - 1

            comp = RLComponents(c, geom=geom, fields=self.fields)
            # Marcos y adornos se repiten en todas las páginas; side_label + watermark también.
            comp.draw_watermark(image_path=watermark_path)
            comp.draw_double_border()
            comp.draw_side_label(side_label_text)

            if is_first:
                comp.draw_header(
                    plantel_nombre=plantel,
                    institucion_nombre=institucion,
                    logo_path=logo_path,
                    tipo_documento=None,
                    folio=None,
                    institucion_clave=institucion_clave or None,
                    registro_sep=registro_sep or None,
                )
                comp.draw_lugar_fecha()
                comp.draw_titulo(self.titulo())

                # Foto a la izquierda + tabla datos alumno a la derecha, con foto_h = tabla_h
                tabla_y_top = body_bottom + 60
                rows = self.datos_rows()
                rh = 22
                tabla_h = max(len(rows) * rh, 110)
                foto_size = tabla_h
                foto_x = comp.content_x
                foto_box_y = tabla_y_top - tabla_h +20 # bottom del box
                foto_box_top_y = foto_box_y + foto_size
                # Dibujar foto (componente global)
                foto_path = ""
                try:
                    from pathlib import Path as _P
                    cand = str(self.fields.get("foto_path") or "")
                    if cand and _P(cand).exists():
                        foto_path = cand
                except Exception:
                    foto_path = ""
                comp.draw_foto_alumno(foto_path, x=foto_x, y=foto_box_y, size=foto_size, width=110, height=140, margin_right=0)
                # Tabla datos a la derecha
                gap = 14
                tabla_x0 = foto_x + foto_size + gap
                tabla_w = (comp.content_x + comp.content_w) - tabla_x0
                after_datos = comp.draw_tabla_datos(
                    rows,
                    y_top=tabla_y_top,
                    x0=tabla_x0,
                    width=tabla_w,
                )
                table_top = after_datos - 18
                after_tabla = comp.draw_tabla_kardex(chunk, y_top=table_top, has_header=True)
            else:
                # Título de continuación + tabla con encabezado, al principio del área útil
                y_cont_title = comp.content_y + comp.content_h - 30
                comp.header_bottom_y = comp.content_y + comp.content_h - 90
                comp.draw_lugar_fecha()
                comp.c.setFillColor(NAVY, 1)
                comp.c.setFont("Helvetica-Bold", 13)
                comp.c.setFillColor(GOLD, 1)
                comp.c.setFont("Helvetica-Bold", 9)
                table_top = y_cont_title + 20 # Separación entre título y tabla
                after_tabla = comp.draw_tabla_kardex(chunk, y_top=table_top, has_header=True)

            if is_last:
                comp.draw_qr_verificacion(
                    folio=str(self.fields.get("folio") or self.fields.get("folio_verif") or ""),
                    url_verificacion=str(self.fields.get("url_verificacion") or ""),
                )
                after_footer_y = comp.draw_footer(
                    after_cierre_y=after_tabla,
                    plantel_contacto=contacto,
                    firmante_nombre=firmante_nombre,
                    firmante_cargo=firmante_cargo,
                    firmante_correo=firmante_correo,
                    firmante_cel=firmante_cel,
                    firma_path=firmante_firma_path,
                    acuerdos=acuerdos,
                    draw_qr=False,
                )
            else:
                comp.draw_qr_verificacion(
                    folio=str(self.fields.get("folio") or self.fields.get("folio_verif") or ""),
                    url_verificacion=str(self.fields.get("url_verificacion") or ""),
                )

            c.showPage()

        c.save()
        return buf.getvalue()
