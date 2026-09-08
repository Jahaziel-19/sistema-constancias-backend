from __future__ import annotations

import base64
import io
import textwrap
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

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


def _wrap(text: str, width_chars: int) -> list[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=width_chars, break_long_words=False)


class TituloBuilder:
    """Título Profesional en PORTRAIT A4 con ornamentación elaborada.

    Patrones de lujo:
    - Borde triple: outer 3pt GOLD (lujoso) · middle 1pt HAIR crema · inner 0.9pt NAVY
    - Esquinas con adornos (cruces doradas + filetes curvos / pequeños "L" con doble línea)
    - Encabezado en 3 niveles: logo + universidad bold navy grande + lema dorado italic
    - Línea fileteada (TRES líneas: GOLD · HAIR · NAVY) bajo header
    - Bloque central de TÍTULO con palabras clave en gold serif grande smallcaps
    - Nombre del egresado en Times-Bold 22pt centrado, entre líneas guía navy/gold
    - Mención de carrera, nivel, modalidad, promedio y periodo.
    - Bloque FOLIO SEP visible centrado con recuadro gold destacado
    - Firmas DOBLES: Rector / Vicerrector Académico (plantilla general) + Autoridad firmante
    - Footer QR + número de Cédula Profesional placeholder y footer institucional
    """

    def __init__(self, fields: Mapping[str, Any]):
        self.fields = dict(fields or {})

    def _get(self, key: str, default: str = "") -> str:
        v = self.fields.get(key)
        return str(v) if v is not None else default

    # --------------------------------------------------------------- ornaments
    def _draw_triple_border(self, comp: RLComponents) -> None:
        c = comp.c
        g = comp.g
        o1 = 6
        o2 = o1 + 4
        o3 = o2 + 6
        x = g.margin_x
        y = g.margin_y
        w = g.width - 2 * g.margin_x
        h = g.height - 2 * g.margin_y
        comp._rect(c, x, y, w, h, stroke=GOLD, lw=3.0)
        comp._rect(c, x + o1, y + o1, w - 2 * o1, h - 2 * o1, stroke=HAIR, lw=0.8)
        comp._rect(c, x + o2, y + o2, w - 2 * o2, h - 2 * o2, stroke=GOLD, lw=1.4)
        comp._rect(c, x + o3, y + o3, w - 2 * o3, h - 2 * o3, stroke=NAVY, lw=0.9)
        # Establecer content area dentro del triple borde
        inset_total = o3 + 12
        comp.content_x = g.margin_x + inset_total
        comp.content_y = g.margin_y + inset_total
        comp.content_w = g.width - 2 * (g.margin_x + inset_total)
        comp.content_h = g.height - 2 * (g.margin_y + inset_total)

    @staticmethod
    def _draw_corner(c, x, y, size, *, flip_x=False, flip_y=False):
        """Pequeño adorno de esquina con dos líneas en L (gold + navy)."""
        sx = -1 if flip_x else 1
        sy = -1 if flip_y else 1
        # L exterior gold grueso
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.8)
        c.line(x, y, x + sx * size, y)
        c.line(x, y, x, y + sy * size)
        # L interior navy fino más adentro
        in_ = size * 0.55
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.7)
        c.line(x + sx * 3, y + sy * 3, x + sx * in_, y + sy * 3)
        c.line(x + sx * 3, y + sy * 3, x + sx * 3, y + sy * in_)
        # Punto central dorado
        c.setFillColor(GOLD)
        c.circle(x, y, 1.8, stroke=0, fill=1)

    def _draw_corners(self, comp: RLComponents) -> None:
        c = comp.c
        g = comp.g
        x_left = g.margin_x + 2
        x_right = g.width - g.margin_x - 2
        y_bottom = g.margin_y + 2
        y_top = g.height - g.margin_y - 2
        s = 26
        self._draw_corner(c, x_left, y_bottom, s, flip_x=False, flip_y=False)
        self._draw_corner(c, x_right, y_bottom, s, flip_x=True, flip_y=False)
        self._draw_corner(c, x_left, y_top, s, flip_x=False, flip_y=True)
        self._draw_corner(c, x_right, y_top, s, flip_x=True, flip_y=True)

    # ---------------------------------------------------------------- header
    def _draw_header(self, comp: RLComponents, *, institucion: str,
                     logo_path: str | None, folio: str, fecha: str) -> float:
        c = comp.c
        x0 = comp.content_x
        w = comp.content_w
        y0 = comp.content_y + comp.content_h

        # Logo centrado arriba (grande 42mm)
        resolved_logo = _resolve_logo(logo_path, self.fields)
        logo_w = logo_h = 42 * mm
        logo_x = x0 + (w - logo_w) / 2
        logo_y = y0 - logo_h
        logo_center_y = logo_y + logo_h / 2
        if resolved_logo:
            try:
                c.drawImage(resolved_logo, logo_x, logo_y, width=logo_w, height=logo_h,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                # Ornamento circular institucional como fallback
                cx = logo_x + logo_w / 2
                cy = logo_center_y
                c.setStrokeColor(GOLD)
                c.setLineWidth(4)
                c.circle(cx, cy, min(logo_w, logo_h) * 0.48, stroke=1, fill=0)
                c.setStrokeColor(NAVY)
                c.setLineWidth(1.2)
                c.circle(cx, cy, min(logo_w, logo_h) * 0.43, stroke=1, fill=0)

        y = logo_y - 14
        # Universidad 32pt bold navy
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 28)
        comp._draw_center(c, institucion.upper(), x0 + w / 2, y)
        y -= 18
        # Slogan gold italic
        c.setFillColor(GOLD)
        c.setFont("Times-Italic", 12)
        comp._draw_center(c, "Autentificación de Documentos · Excelencia Académica", x0 + w / 2, y)
        y -= 14
        # Municipio / estado
        c.setFillColor(TEXT)
        c.setFont("Times-Roman", 10)
        comp._draw_center(c, "Puebla, Puebla · México", x0 + w / 2, y)
        y -= 14

        # Filete triple GOLD · HAIR · NAVY
        for idx, (col, lw) in enumerate([(GOLD, 1.4), (HAIR, 0.6), (NAVY, 0.9)]):
            comp._hrule(c, x0, w, y - idx * 2, color=col, lw=lw)
        y -= 10

        # Folio interno sistema (no SEP) esquina superior derecha
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 8.5)
        c.drawRightString(x0 + w, y + 14, "Número de Folio del Documento")
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(GOLD)
        c.drawRightString(x0 + w, y + 1, folio or "—")
        # Fecha esquina sup izquierda
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 8.5)
        c.drawString(x0, y + 14, "Fecha de Registro")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x0, y + 1, fecha)
        return y - 2

    # ----------------------------------------------------------------- body
    def _draw_media_fila(self, comp: RLComponents, *, y: float) -> float:
        x0 = comp.content_x
        w = comp.content_w
        # -- PALABRA TÍTULO --
        y -= 34
        comp.c.setFillColor(GOLD)
        comp.c.setFont("Times-Bold", 38)
        comp._draw_center(comp.c, "TÍTULO", x0 + w / 2, y)
        y -= 20
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Helvetica", 10)
        comp._draw_center(comp.c, "PROFESIONAL", x0 + w / 2, y)
        y -= 24
        # Filete triple reducido
        line_w = w * 0.55
        line_x = x0 + (w - line_w) / 2
        for idx, (col, lw) in enumerate([(GOLD, 1.2), (HAIR, 0.6), (NAVY, 0.9)]):
            comp._hrule(comp.c, line_x, line_w, y - idx * 2, color=col, lw=lw)
        y -= 20

        # -- Párrafo intro formal --
        intro = (
            "Por medio de la presente, la Autoridad Rectoría de la Institución, "
            "en ejercicio de las facultades que le son conferidas por la Ley de "
            "Educación Superior vigente, concede y OTORGA el presente "
        )
        intro2 = (
            "TÍTULO PROFESIONAL con validez oficial y efectos para todos los "
            "actos de la vida civil y profesional, a favor de:"
        )
        comp.c.setFillColor(TEXT)
        comp.c.setFont("Times-Roman", 12.5)
        for ln in _wrap(intro, 82):
            comp._draw_center(comp.c, ln, x0 + w / 2, y)
            y -= 16
        y -= 2
        for ln in _wrap(intro2, 82):
            comp._draw_center(comp.c, ln, x0 + w / 2, y)
            y -= 16
        y -= 14
        return y

    def _draw_nombre_titulado(self, comp: RLComponents, *, y: float, nombre: str) -> float:
        x0 = comp.content_x
        w = comp.content_w
        # Label
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Helvetica-Bold", 10)
        comp._draw_center(comp.c, "A QUIÉN SE EXPIDE", x0 + w / 2, y)
        y -= 16
        # Línea guía gold arriba del nombre
        line_w = w * 0.78
        line_x = x0 + (w - line_w) / 2
        comp._hrule(comp.c, line_x, line_w, y, color=GOLD, lw=0.9)
        y -= 8
        # Nombre bold grande centrado
        comp.c.setFillColor(TEXT)
        comp.c.setFont("Times-Bold", 22)
        for ln in _wrap(nombre or "—", 52):
            comp._draw_center(comp.c, ln.upper(), x0 + w / 2, y)
            y -= 28
        y += 6
        # Línea guía navy abajo del nombre
        comp._hrule(comp.c, line_x, line_w, y, color=NAVY, lw=0.9)
        y -= 10
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Times-Italic", 9.5)
        comp._draw_center(comp.c, "Nombre del Titular", x0 + w / 2, y)
        y -= 20
        return y

    def _draw_detalles_carrera(
        self,
        comp: RLComponents,
        *,
        y: float,
        carrera: str,
        nivel: str,
        plan: str,
        modalidad: str,
        turno: str,
        promedio: str,
        periodo: str,
    ) -> tuple[float, bool]:
        if not (carrera or nivel or plan or modalidad or turno or promedio or periodo):
            return (y, False)
        x0 = comp.content_x
        w = comp.content_w
        y -= 8
        # Bloque "por haber concluido satisfactoriamente los estudios de..."
        comp.c.setFillColor(TEXT)
        comp.c.setFont("Times-Roman", 11.5)
        comp._draw_center(comp.c, "Por haber concluido satisfactoriamente los estudios de:", x0 + w / 2, y)
        y -= 14
        # Carrera grande
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Times-Bold", 15)
        for ln in _wrap((carrera or "Programa de Estudios").upper(), 62):
            comp._draw_center(comp.c, ln, x0 + w / 2, y)
            y -= 18
        y -= 2
        # Filete corto gold
        line_w = w * 0.4
        line_x = x0 + (w - line_w) / 2
        comp._hrule(comp.c, line_x, line_w, y, color=GOLD, lw=0.8)
        y -= 14
        # Detalles en dos columnas (6 rows => 3 x columna, layout compacto 2 cols x 3 rows)
        left_x = x0 + 28
        right_x = x0 + w / 2 + 22
        row_h = 15
        rows = [
            ("Nivel", nivel),
            ("Turno", turno),
            ("Plan de Estudios", plan),
            ("Promedio General", promedio),
            ("Modalidad", modalidad),
            ("Periodo", periodo),
        ]
        n_cols = 2
        rows_per_col = (len(rows) + n_cols - 1) // n_cols
        for i, (k, v) in enumerate(rows):
            col = i // rows_per_col
            row = i % rows_per_col
            cx = left_x if col == 0 else right_x
            cy = y - row * row_h
            comp.c.setFillColor(NAVY)
            comp.c.setFont("Helvetica-Bold", 8)
            comp.c.drawString(cx, cy + 3, f"{k.upper()}:")
            comp.c.setFillColor(TEXT)
            comp.c.setFont("Times-Roman", 9.5)
            comp.c.drawString(cx + 86, cy + 3, (str(v or "—")).strip() or "—")
        y -= rows_per_col * row_h + 10
        return (y, True)

    def _draw_folio_sep_box(self, comp: RLComponents, *, y: float, folio_sep: str) -> float:
        x0 = comp.content_x
        w = comp.content_w
        box_w = w * 0.55
        box_h = 52
        bx = x0 + (w - box_w) / 2
        by = y - box_h
        # Marco triple
        comp._rect(comp.c, bx, by, box_w, box_h, stroke=GOLD, lw=1.6)
        comp._rect(comp.c, bx + 2.5, by + 2.5, box_w - 5, box_h - 5, stroke=NAVY, lw=0.6)
        comp._rect(comp.c, bx + 5, by + 5, box_w - 10, box_h - 10, stroke=HAIR, lw=0.4)

        # Título del recuadro
        cx = bx + box_w / 2
        comp.c.setFillColor(GOLD)
        comp.c.setFont("Helvetica-Bold", 9)
        comp._draw_center(comp.c, "FOLIO ASIGNADO POR LA S.E.P.", cx, by + box_h - 12)
        # Valor folio sep
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Times-Bold", 15)
        comp._draw_center(comp.c, (folio_sep or "—").upper(), cx, by + box_h - 30)
        # Sub-label
        comp.c.setFillColor(TEXT)
        comp.c.setFont("Times-Italic", 8)
        comp._draw_center(
            comp.c,
            "Número de registro oficial ante la Secretaría de Educación Pública",
            cx,
            by + 6,
        )
        return by - 10

    # ---------------------------------------------------------------- footer
    def _draw_firmas_dobles(
        self,
        comp: RLComponents,
        *,
        y: float,
        autoridad_nombre: str,
        autoridad_cargo: str,
        firma_path: str | None,
    ) -> float:
        x0 = comp.content_x
        w = comp.content_w
        box_w = w * 0.42
        gap = w * 0.12
        left_x = x0 + (w - 2 * box_w - gap) / 2
        right_x = left_x + box_w + gap
        # -- Columna I (Rector) --
        lx = left_x
        ly = y - 4
        comp._hrule(comp.c, lx, box_w, ly, color=NAVY, lw=0.8)
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Times-Bold", 10.5)
        comp._draw_center(comp.c, "Nombre del Rector General", lx + box_w / 2, ly - 14)
        comp.c.setFont("Times-Roman", 9)
        comp._draw_center(comp.c, "Rector General", lx + box_w / 2, ly - 26)

        # -- Columna II (autoridad firmante REAL) --
        rx = right_x
        ry = ly
        comp._hrule(comp.c, rx, box_w, ry, color=GOLD, lw=0.8)
        if firma_path:
            try:
                fw = 96
                fh = 38
                comp.c.drawImage(firma_path, rx + (box_w - fw) / 2, ry + 2,
                                 width=fw, height=fh, preserveAspectRatio=True,
                                 anchor="s", mask="auto")
            except Exception:
                pass
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Times-Bold", 10.5)
        comp._draw_center(comp.c, autoridad_nombre or "Autoridad Facultada", rx + box_w / 2, ry - 14)
        comp.c.setFont("Times-Roman", 9)
        comp._draw_center(comp.c, autoridad_cargo or "Secretario Académico", rx + box_w / 2, ry - 26)

        # Label central bajo ambas firmas
        y_bot = ry - 40
        comp.c.setFillColor(GOLD)
        comp.c.setFont("Helvetica-Bold", 8.5)
        comp._draw_center(comp.c, "FIRMAS DE AUTENTIFICACIÓN", x0 + w / 2, y_bot)
        comp.c.setFont("Times-Italic", 8)
        comp.c.setFillColor(TEXT)
        comp._draw_center(comp.c, "Documento válido con firma autógrafa y sello oficial", x0 + w / 2, y_bot - 11)
        return y_bot - 14

    def _measure_firmas_dobles_h(self) -> float:
        """Altura estimada de firmas dobles (top_start hasta bottom_end) + márgenes."""
        return 96  # ly=4 + 26*2 + 14*2 + separadores = ~96pt

    def _measure_qr_cedula_h(self) -> float:
        """Altura estimada del bloque QR + cédula + labels."""
        return 90  # qr_box=64 + 26 labels = ~90pt

    def _measure_footer_h(self) -> float:
        return 48  # 3 filetes + 3 lines texto

    def _draw_qr_cedula(self, comp: RLComponents, *, y: float, qr_img, folio: str, cedula: str) -> float:
        x0 = comp.content_x
        w = comp.content_w
        qr_box = 64
        qr_x = x0 + 10
        qr_y = y - qr_box
        comp._rect(comp.c, qr_x, qr_y, qr_box, qr_box, stroke=GOLD, lw=0.8)
        comp._rect(comp.c, qr_x + 2, qr_y + 2, qr_box - 4, qr_box - 4, stroke=NAVY, lw=0.4)
        if qr_img is not None:
            try:
                pad = 6
                comp.c.drawImage(qr_img, qr_x + pad, qr_y + pad,
                                 width=qr_box - 2 * pad, height=qr_box - 2 * pad, mask="auto")
            except Exception:
                pass
        # Labels qr (al lado derecho, columna)
        lx = qr_x + qr_box + 14
        ly = y - 8
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Helvetica-Bold", 8.5)
        comp.c.drawString(lx, ly, "VERIFICACIÓN DIGITAL")
        ly -= 12
        comp.c.setFont("Times-Roman", 8.5)
        comp.c.setFillColor(TEXT)
        comp.c.drawString(lx, ly, "Escanee el código QR para verificar la autenticidad del documento.")
        ly -= 12
        comp.c.drawString(lx, ly, f"Folio de verificación: {folio or '—'}")
        ly -= 12
        # Cédula profesional (placeholder)
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Helvetica-Bold", 8.5)
        comp.c.drawString(lx, ly, "CÉDULA PROFESIONAL")
        ly -= 12
        comp.c.setFont("Times-Roman", 8.5)
        comp.c.setFillColor(TEXT)
        comp.c.drawString(lx, ly, cedula or "(trámite de registro S.E.P. ante la Dirección General de Profesiones)")
        ly -= 14
        return min(ly, qr_y - 6)

    def _draw_footer_institucional(self, comp: RLComponents, *, y: float, institucion: str) -> None:
        x0 = comp.content_x
        w = comp.content_w
        # Filete triple arriba
        for idx, (col, lw) in enumerate([(NAVY, 0.9), (HAIR, 0.6), (GOLD, 1.0)]):
            comp._hrule(comp.c, x0, w, y - idx * 1.6, color=col, lw=lw)
        y -= 14
        comp.c.setFillColor(NAVY)
        comp.c.setFont("Helvetica-Bold", 7.5)
        comp._draw_center(comp.c, institucion.upper(), x0 + w / 2, y)
        y -= 10
        comp.c.setFillColor(TEXT)
        comp.c.setFont("Times-Roman", 7.5)
        comp._draw_center(comp.c, "Documento digital emitido con firma electrónica avanzada.", x0 + w / 2, y)
        y -= 9
        comp.c.setFont("Times-Italic", 7)
        comp._draw_center(comp.c, "Este documento puede ser verificado públicamente mediante el código QR impreso.", x0 + w / 2, y)

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
        w, h = A4
        geom = PageGeometry(width=w, height=h, margin_x=22, margin_y=22)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        comp = RLComponents(c, geom=geom, fields=self.fields)

        # Resolver watermark PERO NO dibujarlo con draw_watermark (centro absoluto tapa texto).
        resolved_watermark: Path | None = None
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
        if watermark_path and Path(watermark_path).exists():
            resolved_watermark = Path(watermark_path)

        # 1) Borde triple ornamentado + esquinas
        self._draw_triple_border(comp)
        self._draw_corners(comp)

        institucion = self._get("institucion_nombre") or "Colegio Universitario Hispana"
        folio = self._get("folio") or self._get("folio_verif") or "—"
        fecha = _fecha_registro(date.today())
        after_header = self._draw_header(
            comp, institucion=institucion, logo_path=logo_path, folio=folio, fecha=fecha,
        )

        # ==============================================================================
        # CALCULO ESTRICTO DEL FOOTER (COORDENADAS FIJAS, NO DEPENDEN DE y DEL BODY)
        # ==============================================================================
        # Eje ReportLab: Y=0 es la INFERIOR de la página. Y ALTO = arriba. Y BAJO = abajo.
        # BODY se dibuja de after_header (Y≈780, MUY ARRIBA) hacia abajo (Y decrece).
        # FOOTER siempre debe estar EN LA PARTE INFERIOR (cerca de content_y ≈ 50).

        footer_pad = 10  # margen mínimo sobre el borde INFERIOR del content area
        footer_bottom_y = comp.content_y + footer_pad  # ≈ 60 (Punto más BAJO del footer)

        # Altura total medida de firmas + gaps + QR + footer institucional.
        h_firmas = self._measure_firmas_dobles_h()  # ≈ 96
        h_qr = self._measure_qr_cedula_h()           # ≈ 90
        h_footer = self._measure_footer_h()          # ≈ 48
        gap_firmas_qr = 12
        gap_qr_footer = 6
        footer_total_h = h_firmas + gap_firmas_qr + h_qr + gap_qr_footer + h_footer  # ≈ 252

        # Punto SUPERIOR (más alto) del footer: la línea hrule de firmas empieza aquí.
        footer_top_y = footer_bottom_y + footer_total_h  # ≈ 60 + 252 = 312.

        # El body NO DEBE EXTENDERSE MÁS ABAJO de body_ceiling_y (debe quedar 20pt encima de footer).
        # Si después de dibujar el body, y < body_ceiling_y → estamos demasiado abajo, pero cortamos el folio_sep al techo.
        body_ceiling_y = footer_top_y + 26  # ≈ 338

        # Puntos fijos para cada sección del footer:
        y_firmas_start = footer_top_y                           # ≈ 312 (firmas empiezan aquí hacia abajo)
        y_qr_start = y_firmas_start - h_firmas - gap_firmas_qr  # ≈ 312 - 96 - 12 = 204
        y_footer_start = footer_bottom_y + h_footer             # ≈ 108 (institucional desde 108 hacia abajo)

        # ==============================================================================
        # BODY (solo en la zona segura: after_header hasta body_ceiling_y)
        # ==============================================================================
        y = self._draw_media_fila(comp, y=after_header)
        nombre = self._get("nombre") or self._get("nombre_completo") or "—"
        y = self._draw_nombre_titulado(comp, y=y, nombre=nombre)

        carrera = self._get("carrera_nombre") or self._get("carrera") or ""
        nivel = self._get("nivel_actual_ordinal") or self._get("nivel") or ""
        plan = self._get("plan_estudios") or self._get("clave_plan") or self._get("ciclo_escolar_clave") or ""
        modalidad = self._get("modalidad") or ""
        turno = self._get("turno") or ""
        promedio = str(self._get("promedio_general") or self._get("promedio_periodo") or "—")
        periodo = (self._get("periodo_nombre") or "") + " " + (self._get("ciclo_escolar_clave") or "")
        y, _ = self._draw_detalles_carrera(
            comp, y=y, carrera=carrera, nivel=nivel, plan=plan,
            modalidad=modalidad, turno=turno, promedio=promedio, periodo=periodo,
        )
        y -= 10

        # --- Watermark manual: centrado horizontal, ENTRE detalles_carrera (y actual) y body_ceiling_y. ---
        # safe_top = extremo superior (mayor Y) en el que se permite watermark = detalles_carrera - 8
        # safe_bot = extremo inferior (menor Y) = body_ceiling_y - 14 (antes empieza firma)
        if resolved_watermark is not None:
            try:
                safe_top = y - 8
                safe_bot = body_ceiling_y + 14  # +14 porque body_ceiling_y ya incluye 26pt sobre footer_top
                if safe_top > safe_bot + 130:  # si hay ≥130pt de hueco
                    wm_y_center = (safe_top + safe_bot) / 2
                    wm_w = min(comp.content_w * 0.38, 190)
                    wm_h = wm_w
                    wm_x = comp.content_x + (comp.content_w - wm_w) / 2
                    wm_y = wm_y_center - wm_h / 2
                    c.saveState()
                    c.drawImage(
                        str(resolved_watermark), wm_x, wm_y,
                        width=wm_w, height=wm_h,
                        preserveAspectRatio=True, anchor="c", mask="auto",
                    )
                    c.restoreState()
            except Exception:
                pass

        folio_sep = self._get("folio_sep") or ""
        # Folio SEP box ocupa 52pt + 10 = 62pt vertical. Si lo dibujamos con y actual, sobrepasamos body_ceiling?
        # Forzar: "Si folio_sep_box terminara más abajo que body_ceiling_y, iniciarlo más arriba."
        folio_box_h = 62
        if y - folio_box_h < body_ceiling_y:
            y = body_ceiling_y + folio_box_h
        y = self._draw_folio_sep_box(comp, y=y, folio_sep=folio_sep)

        # ==============================================================================
        # FOOTER (COORDENADAS FIJAS, no usan y del body excepto fallback)
        # ==============================================================================
        qr_img = _decode_qr(self._get("qr_png_base64") or "")

        # --- Firmas Dobles (FIJO en y_firmas_start) ---
        _ = self._draw_firmas_dobles(
            comp, y=y_firmas_start,
            autoridad_nombre=firmante_nombre or "",
            autoridad_cargo=firmante_cargo or "",
            firma_path=firmante_firma_path,
        )

        # --- QR + Cédula (FIJO en y_qr_start) ---
        _ = self._draw_qr_cedula(comp, y=y_qr_start, qr_img=qr_img, folio=folio, cedula=(self._get("cedula_profesional") or ""))

        # --- Footer institucional (FIJO en y_footer_start) ---
        self._draw_footer_institucional(comp, y=y_footer_start, institucion=institucion)

        c.showPage()
        c.save()
        return buf.getvalue()


def build_titulo(
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
    builder = TituloBuilder(fields)
    if institucion_nombre and "institucion_nombre" not in builder.fields:
        builder.fields["institucion_nombre"] = institucion_nombre
    return builder.build(
        logo_path=logo_path,
        firmante_nombre=firmante_nombre,
        firmante_cargo=firmante_cargo,
        firmante_firma_path=firmante_firma_path,
        watermark_path=watermark_path,
    )
