from __future__ import annotations

import base64
import io
import textwrap
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from uh_documentos.pdf.components.base import (
    GOLD,
    NAVY,
    HAIR,
    TEXT,
    PageGeometry,
    RLComponents,
)


def _decode_qr(qr_b64: str) -> ImageReader | None:
    if not qr_b64:
        return None
    try:
        raw = base64.b64decode(qr_b64)
        return ImageReader(io.BytesIO(raw))
    except Exception:
        return None


def _fecha_registro(dt: date) -> str:
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    return f"{dt.day} de {meses[dt.month - 1]} de {dt.year}"


def _resolve_logo(logo_path: str | None, fields: Mapping[str, Any]) -> str | None:
    cands: list[str] = []
    if logo_path:
        cands.append(logo_path)
    cands.extend([
        str(fields.get("logo_path_institucional") or ""),
        str(fields.get("logo_path") or ""),
    ])
    try:
        from django.conf import settings as _s
        base = Path(_s.MEDIA_ROOT)
        for sub in ("logos", "logo", "institucion", "general", "plantel"):
            for fname in (
                "logo_hispana.png", "logo.png", "logo_institucional.png",
                "logo_plantel.png", "logo_hispana.jpg", "logo.jpg",
            ):
                cands.append(str(base / sub / fname))
    except Exception:
        pass
    for cand in cands:
        if not cand:
            continue
        try:
            if Path(cand).exists():
                return cand
        except Exception:
            continue
    return None


class DiplomaReconocimientoBuilder:
    """Diploma / Reconocimiento en LANDSCAPE A4 — estilo institucional limpio.

    Mantiene de constancias: doble borde (GOLD/NAVY), watermark transparente,
    tipografía serif Times + sans Helvetica, líneas guía HAIR en lugar de recuadros.
    El espacio sobrante tras quitar labels auxiliares se dedica íntegramente al
    párrafo CENTRADO y AMPLIO de la descripción del nombramiento.
    """

    def __init__(self, fields: Mapping[str, Any]):
        self.fields = dict(fields or {})

    # --------------------------------------------------------------- utilidades
    def _get(self, key: str, default: str = "") -> str:
        v = self.fields.get(key)
        return str(v) if v is not None else default

    @staticmethod
    def _wrap(text: str, width_chars: int) -> list[str]:
        if not text:
            return []
        return textwrap.wrap(text, width=width_chars, break_long_words=False)

    # ----------------------------------------------------------------- dibujos
    def _draw_header_custom(
        self,
        comp: RLComponents,
        *,
        institucion_nombre: str,
        logo_path: str | None,
        folio: str,
        fecha_str: str,
    ) -> float:
        c = comp.c
        x0 = comp.content_x
        y0 = comp.content_y + comp.content_h
        w = comp.content_w

        # -- Logo (izquierda)
        resolved_logo = _resolve_logo(logo_path, self.fields)
        logo_x = x0 + 8
        logo_max_h = 92
        logo_max_w = 92
        logo_drawn_h = logo_max_h
        if resolved_logo:
            try:
                img = ImageReader(resolved_logo)
                img_w, img_h = img.getSize()
                scale = min(logo_max_h / img_h, logo_max_w / img_w, 1.0)
                dw = img_w * scale
                dh = img_h * scale
                c.drawImage(resolved_logo, logo_x, y0 - dh, width=dw, height=dh,
                            preserveAspectRatio=True, mask="auto")
                logo_drawn_h = dh
            except Exception:
                pass
        logo_center_y = y0 - logo_drawn_h / 2

        # -- Columna central (institución)
        center_x = x0 + w / 2
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 20)
        comp._draw_center(c, institucion_nombre, center_x, logo_center_y + 24)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 11)
        comp._draw_center(c, "Autentificación de Documentos", center_x, logo_center_y + 6)
        # (Puebla, México) se omitió conforme a edición del usuario

        # -- Columna derecha (folio + fecha)
        right_x = x0 + w
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 10)
        c.drawRightString(right_x, logo_center_y + 28, "Número de Folio del Documento")
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(NAVY)
        c.drawRightString(right_x, logo_center_y + 8, folio or "")
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 10)
        c.drawRightString(right_x, logo_center_y - 12, "Fecha de Registro")
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(right_x, logo_center_y - 28, fecha_str)

        # -- Separadores
        sep_y = logo_center_y - 48
        comp._hrule(c, x0, w, sep_y, color=NAVY, lw=0.35)
        comp._hrule(c, x0, w, sep_y - 3, color=GOLD, lw=0.25)
        return sep_y - 3

    def _draw_body(
        self,
        comp: RLComponents,
        *,
        top_y: float,
        footer_top: float,
        nombre: str,
        descripcion: str,
        institucion_otorga: str,
    ) -> float:
        """Dibuja el cuerpo aprovechando TODO el espacio libre entre header y footer.

        Parámetro `footer_top` = y mínima (más alta en la página) que NO debe
        traspasar el cuerpo para no solaparse con QR y firmas.
        """
        c = comp.c
        x0 = comp.content_x
        w = comp.content_w
        y = top_y - 12

        # -- "Se expide a:" label izquierdo navy
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 11)
        c.drawString(x0 + 30, y, "Se expide a:")
        y -= 18

        # -- Nombre CENTRADO grande, Times-Bold mayúsculas
        c.setFillColor(TEXT)
        c.setFont("Times-Bold", 22)
        lines_nombre = self._wrap(nombre or "—", 60)
        for line in lines_nombre:
            comp._draw_center(c, line.upper(), x0 + w / 2, y)
            y -= 28
        y -= 4

        # -- Línea guía debajo del nombre
        line_w = w * 0.82
        line_x = x0 + (w - line_w) / 2
        # (sin HAIR line visible para usuario que reportó cruces — se sustituye
        # por un par de marcadores en los extremos, invisible si no hay que adornar)
        # comp._hrule(c, line_x, line_w, y, color=HAIR, lw=0.4, dash=(2,2))
        y -= 24

        # ----------------------------------------------------------
        # NOMBRAMIENTO / DESCRIPCIÓN AMPLIO Y CENTRADO
        # Usar TODO el espacio vertical disponible entre el nombre y
        # el bloque "Institución que otorga" (antes del footer).
        # ----------------------------------------------------------
        reserva_institucion = 78  # espacio para label + valor + linea guia
        inst_top = footer_top - reserva_institucion
        # Dejar 18pt de separación min entre fin descripción y label institución
        avail_top = y
        avail_bottom = inst_top - 18
        avail_h = max(avail_top - avail_bottom, 60)

        # Medir el texto con fuentes crecientes para usar la más grande que entre.
        motivo = (descripcion or "").strip() or "—"
        # Quitar preámbulo comentado: render solo la descripción que escribió
        # el usuario (es decir, el motivo puro).
        paragraphs_raw = [p for p in [ln.strip() for ln in motivo.split("\n")] if p]
        motivo_flat = "  \n\n  ".join(paragraphs_raw) if paragraphs_raw else motivo

        # Opciones de tamaño: preferimos la mayor fuente ajustable al espacio.
        size_options: list[tuple[int, int]] = [
            (18, 68),  # font_size, wrap_chars aprox
            (16.5, 72),
            (15, 78),
            (14, 84),
            (13, 92),
            (12, 100),
            (11, 110),
        ]

        chosen_size = size_options[-1][0]
        chosen_wrap = size_options[-1][1]
        chosen_lines: list[str] = []
        lead_add = 4

        for fsize, wrap_c in size_options:
            lead = fsize + lead_add + 1
            # Construir líneas wrappeadas (respetando dobles saltos como separadores)
            if paragraphs_raw:
                collected: list[str] = []
                for p in paragraphs_raw:
                    collected.extend(self._wrap(p, wrap_c))
                    collected.append("")  # spacer entre párrafos (último no cuenta)
                while collected and collected[-1] == "":
                    collected.pop()
            else:
                collected = self._wrap(motivo_flat, wrap_c)
            total_h = len(collected) * lead
            if total_h <= avail_h:
                chosen_size = fsize
                chosen_wrap = wrap_c
                chosen_lines = collected
                # Si todavía sobra mucho espacio, aceptar pero igual no subir
                break

        # Si el loop terminó con la más pequeña pero no entra: usamos la más
        # pequeña aunque exceda (no debe pasar por avail_h razonable).
        if not chosen_lines:
            chosen_lines = self._wrap(motivo_flat, chosen_wrap)

        chosen_lead = chosen_size + lead_add + 1

        # Centrar VERTICALMENTE el bloque de descripción dentro de [avail_bottom, avail_top]
        total_h = len(chosen_lines) * chosen_lead
        block_top = avail_bottom + (avail_h - total_h) / 2 + total_h
        block_top = min(block_top, avail_top - 6)  # margen superior

        y_desc = block_top
        c.setFillColor(TEXT)
        c.setFont("Times-Roman", chosen_size)
        for line in chosen_lines:
            if line == "":
                y_desc -= chosen_lead
                continue
            comp._draw_center(c, line, x0 + w / 2, y_desc)
            y_desc -= chosen_lead

        # ----------------------------------------------------------
        # Institución que otorga — centrado al final del cuerpo
        # ----------------------------------------------------------
        y_inst = inst_top
        c.setFillColor(GOLD)
        c.setFont("Helvetica", 11)
        comp._draw_center(c, "Institución que otorga", x0 + w / 2, y_inst)
        y_inst -= 14
        c.setFillColor(NAVY)
        c.setFont("Times-Bold", 14)
        inst_lines = self._wrap(institucion_otorga or "Colegio Universitario Hispana", 74)
        for line in inst_lines:
            comp._draw_center(c, line.upper(), x0 + w / 2, y_inst)
            y_inst -= 20
        # (sin línea guía bajo institución — usuario reportó cruce con QR/firmas)
        return y_inst - 10

    def _draw_footer(
        self,
        comp: RLComponents,
        *,
        qr_img: ImageReader | None,
        firmante_nombre: str,
        firmante_cargo: str,
        firma_path: str | None,
        folio: str,
    ) -> float:
        """Dibuja footer. Devuelve la coordenada Y mínima (altura del footer en puntos).

        El cuerpo NO debe invadir `content_y + HEIGHT_MIN`.
        """
        c = comp.c
        x0 = comp.content_x
        w = comp.content_w
        bottom_y = comp.content_y + 10

        # -- QR block (izq)  — más pequeño para no pegar con instituciones
        qr_box = 96
        qr_x = x0 + 28
        qr_y = bottom_y
        comp._rect(c, qr_x, qr_y, qr_box, qr_box, stroke=GOLD, lw=0.7)
        if qr_img is not None:
            try:
                pad = 5
                c.drawImage(qr_img, qr_x + pad, qr_y + pad,
                            width=qr_box - 2 * pad, height=qr_box - 2 * pad, mask="auto")
            except Exception:
                pass
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(qr_x, qr_y + qr_box + 6, "CÓDIGO QR AUTENTIFICADOR")
        if folio:
            c.setFont("Times-Italic", 7.5)
            c.drawString(qr_x, qr_y - 9, f"Folio: {folio}")

        # -- Firma block (parte derecha, separada de QR)  — ancho menor, anclado al centro-izquierda del 55% del papel
        sig_box_w = 240
        sig_x = x0 + w - sig_box_w - 40
        sig_line_y = bottom_y + 54
        comp._hrule(c, sig_x, sig_box_w, sig_line_y, color=NAVY, lw=0.6)

        if firma_path:
            try:
                fw = 140
                fh = 52
                c.drawImage(firma_path, sig_x + (sig_box_w - fw) / 2, sig_line_y + 4,
                            width=fw, height=fh, preserveAspectRatio=True,
                            anchor="s", mask="auto")
            except Exception:
                pass

        c.setFillColor(TEXT)
        c.setFont("Times-Bold", 11.5)
        comp._draw_center(c, firmante_nombre or "—", sig_x + sig_box_w / 2, sig_line_y - 15)
        c.setFont("Times-Roman", 9.5)
        comp._draw_center(c, firmante_cargo or "Autoridad facultada", sig_x + sig_box_w / 2, sig_line_y - 28)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8)
        comp._draw_center(c, "FIRMA DE AUTENTIFICACIÓN", sig_x + sig_box_w / 2, sig_line_y - 44)

        # Altura mínima que ocupa el footer contando el label QR y márgenes superiores
        top_qr = qr_y + qr_box + 18  # label + buffer visual
        top_sig = sig_line_y + 4 + 56 + 6  # imagen firma + buffer
        return max(top_qr, top_sig, bottom_y + 170)

    # ------------------------------------------------------------------ build
    def build(
        self,
        *,
        logo_path: str | None = None,
        firmante_nombre: str | None = None,
        firmante_cargo: str | None = None,
        firmante_firma_path: str | None = None,
        watermark_path: str | None = None,
    ) -> bytes:
        w, h = landscape(A4)
        geom = PageGeometry(width=w, height=h, margin_x=30, margin_y=30)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        comp = RLComponents(c, geom=geom, fields=self.fields)

        if not watermark_path:
            try:
                from django.conf import settings
                base = Path(settings.MEDIA_ROOT)
                for cand in [
                    base / "watermark" / "marca_agua.png",
                    base / "watemark" / "marca_agua.png",
                ]:
                    if cand.exists():
                        watermark_path = str(cand)
                        break
            except Exception:
                pass
        comp.draw_watermark(text="", image_path=watermark_path)
        comp.draw_double_border(outer_w=2.0, inner_w=0.7)

        institucion = self._get("institucion_nombre") or "Colegio Universitario Hispana"
        folio = self._get("folio") or self._get("folio_verif") or "—"
        fecha = _fecha_registro(date.today())
        header_bottom = self._draw_header_custom(
            comp,
            institucion_nombre=institucion,
            logo_path=logo_path,
            folio=folio,
            fecha_str=fecha,
        )

        qr_img = _decode_qr(self._get("qr_png_base64") or "")
        # Buffer amplio (260pt) para evitar cualquier cruce de elementos.
        footer_top = comp.content_y + 260

        nombre = self._get("nombre") or self._get("nombre_completo") or "—"
        descripcion = self._get("descripcion_nombramiento") or self._get("motivo") or ""
        institucion_otorga = (
            self._get("institucion_otorgante") or self._get("institucion") or institucion
        )
        self._draw_body(
            comp,
            top_y=header_bottom,
            footer_top=footer_top,
            nombre=nombre,
            descripcion=descripcion,
            institucion_otorga=institucion_otorga,
        )
        self._draw_footer(
            comp,
            qr_img=qr_img,
            firmante_nombre=firmante_nombre or "",
            firmante_cargo=firmante_cargo or "",
            firma_path=firmante_firma_path,
            folio=folio,
        )

        c.showPage()
        c.save()
        return buf.getvalue()


def build_diploma_reconocimiento(
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
    # plantel_nombre / plantel_contacto / acuerdos / plantel_obj se ignoran
    # (no se puede colocar el nombre del plantel en el header).
    builder = DiplomaReconocimientoBuilder(fields)
    if institucion_nombre and "institucion_nombre" not in builder.fields:
        builder.fields["institucion_nombre"] = institucion_nombre
    return builder.build(
        logo_path=logo_path,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )
