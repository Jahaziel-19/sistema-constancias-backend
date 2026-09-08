from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Mapping

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

NAVY = "#1c3660"
GOLD = "#a9822f"
HAIR = "#c9bd9c"
RED_ACC = "#7a1f1f"
TEXT = "#1b1b1b"
BG_ROW = "#fbf7ec"
MARCA_BG = "#fff7d9"


@dataclass
class PageGeometry:
    width: float
    height: float
    margin_x: float
    margin_y: float


class RLComponents:
    def __init__(self, canvas, *, geom: PageGeometry, fields: Mapping[str, Any]):
        self.c = canvas
        self.g = geom
        self.f = fields

    def draw_double_border(self, *, outer_color=GOLD, inner_color=NAVY, outer_w: float = 2.2, inner_w: float = 0.8):
        c = self.c
        g = self.g
        inset1 = 10
        inset2 = inset1 + 10
        self._rect(c, g.margin_x, g.margin_y, g.width - 2 * g.margin_x, g.height - 2 * g.margin_y, stroke=outer_color, lw=outer_w)
        self._rect(c, g.margin_x + inset1, g.margin_y + inset1, g.width - 2 * (g.margin_x + inset1), g.height - 2 * (g.margin_y + inset1), stroke=inner_color, lw=inner_w)
        self.content_x = g.margin_x + inset2
        self.content_y = g.margin_y + inset2
        self.content_w = g.width - 2 * (g.margin_x + inset2)
        self.content_h = g.height - 2 * (g.margin_y + inset2)

    def draw_watermark(self, text: str = "", image_path: str | None = None):
        c = self.c
        g = self.g
        c.saveState()
        try:
            if image_path:
                try:
                    from reportlab.lib.utils import ImageReader
                    img = ImageReader(image_path)
                    img_w, img_h = img.getSize()
                    max_w = g.width * 0.7
                    max_h = g.height * 0.7
                    scale = min(max_w / img_w, max_h / img_h, 1.0)
                    draw_w = img_w * scale
                    draw_h = img_h * scale
                    x = (g.width - draw_w) / 2
                    y = (g.height - draw_h) / 2
                    c.drawImage(image_path, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True)
                except Exception:
                    pass
            elif text:
                c.setFillColor(NAVY, 0.05)
                from reportlab.pdfbase.pdfmetrics import stringWidth
                fs = 132
                w = stringWidth(text, "Helvetica-Bold", fs)
                c.translate(g.width / 2, g.height / 2 + 30)
                c.setFont("Helvetica-Bold", fs)
                c.drawString(-w / 2, -fs / 2, text)
        finally:
            c.restoreState()

    def draw_side_label(self, text: str = "CONSTANCIA DE ESTUDIOS"):
        c = self.c
        g = self.g
        c.saveState()
        try:
            x = g.margin_x + 3
            y = g.height / 2
            c.translate(x, y)
            c.rotate(90)
            from reportlab.pdfbase.pdfmetrics import stringWidth
            fs = 10
            c.setFont("Helvetica-Bold", fs)
            c.setFillColor(GOLD, 1)
            chars = list(text.replace(" ", "  "))
            rendered = "   ".join(chars) if len(text) <= 30 else text
            w = stringWidth(rendered, "Helvetica-Bold", fs)
            c.drawString(-w / 2, -fs / 2, rendered)
        finally:
            c.restoreState()

    def draw_header(self, *, area_emisora: str | None = None, plantel_nombre: str | None = None, institucion_nombre: str | None = None, logo_path: str | None = None, tipo_documento: str | None = None, folio: str | None = None, institucion_clave: str | None = None, registro_sep: str | None = None):
        c = self.c
        f = self.f
        x0 = self.content_x
        y0 = self.content_y + self.content_h

        def _pick_logo_path() -> str | None:
            cands: list[str] = []
            if logo_path:
                cands.append(logo_path)
            cands.extend([str(f.get("logo_path_institucional") or ""), str(f.get("logo_path") or "")])
            try:
                from django.conf import settings as _s
                from pathlib import Path as _P
                base = _P(_s.MEDIA_ROOT)
                for sub in ("logos", "logo", "institucion", "general", "plantel"):
                    for fname in ("logo_hispana.png", "logo.png", "logo_institucional.png", "logo_plantel.png", "logo_hispana.jpg", "logo.jpg"):
                        cands.append(str(base / sub / fname))
            except Exception:
                pass
            for cand in cands:
                if not cand:
                    continue
                try:
                    from pathlib import Path as _P
                    if _P(cand).exists():
                        return cand
                except Exception:
                    continue
            return None

        resolved_logo = _pick_logo_path()

        logo_h = 100
        logo_w = 100
        logo_x = x0 + 10
        logo_y = y0 - logo_h
        if resolved_logo:
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(resolved_logo)
                img_w, img_h = img.getSize()
                max_logo_h = 130
                max_logo_w = 130
                scale = min(max_logo_h / img_h, max_logo_w / img_w, 1.0)
                logo_w = img_w * scale
                logo_h = img_h * scale
                logo_x = x0 + 10
                logo_y = y0 - logo_h
                c.drawImage(resolved_logo, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        # Logo
        logo_center_y = logo_y + logo_h / 2
        center_x = x0 + 290 #+ self.content_w / 2
        
        # Título
        title_y = logo_center_y + 20
        c.setFillColor(NAVY, 1)
        c.setFont("Helvetica-Bold", 18)
        self._draw_center(c, institucion_nombre if institucion_nombre is not None else str(f.get("institucion_nombre") or "Colegio Universitario Hispana"), center_x, title_y)
        
        # Subtítulo
        subtitle_y = title_y - 22
        c.setFillColor(GOLD, 1)
        c.setFont("Helvetica-Bold", 10.5)
        plantel_texto = plantel_nombre if plantel_nombre is not None else str(f.get("plantel_nombre") or "")
        self._draw_center(c, plantel_texto, center_x, subtitle_y)
        
        # Clave
        clave_y = subtitle_y - 16
        clave_texto = institucion_clave if institucion_clave is not None else str(f.get("institucion_clave") or "")
        # Registro SEP
        sep_texto = registro_sep if registro_sep is not None else str(f.get("registro_sep") or "")
        plantel_clave = str(f.get("plantel_clave") or "")
        partes_clave: list[str] = []
        if plantel_clave:
            partes_clave.append(f"Clave plantel: {plantel_clave}")
        if clave_texto and clave_texto != plantel_clave:
            partes_clave.append(f"RGP: {clave_texto}")
        if sep_texto:
            partes_clave.append(f"Reg. SEP: {sep_texto}")
        clave_combined = " · ".join(partes_clave)
        if clave_combined:
            c.setFillColor("#555555", 1)
            c.setFont("Times-Roman", 8)
            self._draw_center(c, clave_combined, center_x, clave_y)
            sep_y = clave_y - 50 #el espacio entre el último texto del header (clave/RGP/SEP) y la línea. Si lo aumentas, la línea baja.
        else:
            sep_y = subtitle_y - 12

        self._hrule(c, x0, self.content_w, sep_y, color=NAVY, lw=0.3, dash=None)
        self.header_bottom_y = sep_y

    def draw_lugar_fecha(self, *, default: str = ""):
        c = self.c
        f = self.f
        header_bottom = getattr(self, "header_bottom_y", None)
        if header_bottom is None:
            header_bottom = getattr(self, "content_y", 0) + getattr(self, "content_h", 0) - 90
        y = header_bottom - 10
        c.setFillColor(TEXT, 1)
        c.setFont("Times-Italic", 11)
        lugar_fecha = str(f.get("lugar_fecha") or default)
        if not lugar_fecha:
            from datetime import datetime
            now = datetime.now()
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            ]
            lugar_fecha = f"a {now.day} de {meses[now.month - 1]} de {now.year}"
        if lugar_fecha:
            self._draw_right(c, lugar_fecha, self.content_x + self.content_w, y)
        self.after_lugar_fecha_y = y - 22

    def draw_titulo(self, text: str | None = None):
        c = self.c
        f = self.f
        y0 = getattr(self, "after_lugar_fecha_y", self.content_y + self.content_h - 140)
        h = 32
        x0 = self.content_x
        w = self.content_w
        self._hrule(c, x0, w, y0, color=GOLD, lw=1.2)
        self._hrule(c, x0, w, y0 - h, color=GOLD, lw=1.2)
        c.setFillColor(NAVY, 1)
        c.setFont("Helvetica-Bold", 13)
        txt = text or str(f.get("tipo_documento") or "Constancia de Estudios")
        self._draw_center(c, txt, x0 + w / 2, y0 - h / 2 - 5)
        self.after_titulo_y = y0 - h - 22

    def draw_destinatario(self, text: str = "A QUIEN CORRESPONDA:"):
        c = self.c
        y = getattr(self, "after_titulo_y", self.content_y + self.content_h - 200)
        c.setFillColor(NAVY, 1)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(self.content_x, y, text)
        self.after_dest_y = y - 24

    def draw_paragraph_with_marcas(self, text_segments: list[tuple[str, bool]], *, y: float | None = None, leading: float = 14, word_spacing: float = 0.4) -> float:
        c = self.c
        f = self.f
        x0 = self.content_x
        w = self.content_w
        cur_y = y if y is not None else getattr(self, "after_dest_y", self.content_y + self.content_h - 240)
        left = x0
        top = cur_y
        c.setFillColor(TEXT, 1)
        c.setFont("Times-Roman", 11)
        from reportlab.pdfbase.pdfmetrics import stringWidth

        line_h = leading
        y_off = 0
        def advance_y():
            nonlocal y_off, left
            y_off += line_h
            left = x0
        for raw, is_marca in text_segments:
            if not raw:
                continue
            tokens = self._split_tokens(raw)
            for tok in tokens:
                if tok == "\n":
                    advance_y()
                    continue
                font_name = "Times-Bold" if is_marca else "Times-Roman"
                fs = 11
                space_w = stringWidth(" ", font_name, fs) + word_spacing
                tok_w = stringWidth(tok, font_name, fs)
                if left + tok_w > x0 + w + 0.01:
                    advance_y()
                if is_marca:
                    pad_x = 2
                    pad_y = 1.2
                    c.setFillColor(MARCA_BG, 1)
                    c.rect(left - pad_x, top - y_off - fs - pad_y, tok_w + pad_x * 2, fs + pad_y * 1.6, stroke=0, fill=1)
                    c.setLineWidth(0.7)
                    c.setStrokeColor(GOLD, 1)
                    c.line(left - pad_x, top - y_off - fs - pad_y, left - pad_x + tok_w + pad_x * 2, top - y_off - fs - pad_y)
                    c.setStrokeColor(TEXT, 0)
                c.setFillColor(NAVY if is_marca else TEXT, 1)
                c.setFont(font_name, fs)
                c.drawString(left, top - y_off - fs, tok)
                left += tok_w + space_w
        return top - y_off - line_h

    def draw_tabla_datos(self, rows: list[tuple[str, str]], *, y_top: float | None = None, label_pct: float = 0.34, x0: float | None = None, width: float | None = None) -> float:
        c = self.c
        x0 = x0 if x0 is not None else self.content_x
        w = width if width is not None else self.content_w
        if y_top is None:
            y_top = self._last_body_bottom(self.content_y + 90) - 22
        rh = 18
        h = len(rows) * rh
        self._rect(c, x0, y_top - h, w, h, stroke=HAIR, fill=BG_ROW, lw=0.7)
        lbl_w = int(w * label_pct)
        for i, (lbl, val) in enumerate(rows):
            ry = y_top - (i + 1) * rh
            self._hrule(c, x0, w, ry, color="#b6ab8a", lw=0.4, dash=[2, 2])
            self._vrule(c, x0 + lbl_w, 0, 0, 0, color="#b6ab8a", lw=0.4)
            c.setFillColor(NAVY, 1)
            c.setFont("Helvetica-Bold", 7.5)
            self._draw_safe(c, str(lbl), x0 + 8, ry + rh / 2 - 3)
            c.setFillColor(TEXT, 1)
            c.setFont("Times-Roman", 9)
            self._draw_safe(c, str(val or ""), x0 + lbl_w + 10, ry + rh / 2 - 3)
        self._vrule(c, x0 + lbl_w, 0, 0, 0, color=HAIR, lw=0.0, force=False) or None
        return y_top - h - 18

    def draw_tabla_kardex(self, materias: list[dict[str, Any]], *, y_top: float | None = None, has_header: bool = True, continuation_title: str = "Kardex (continuación)") -> float:
        c = self.c
        x0 = self.content_x
        w = self.content_w
        if y_top is None:
            y_top = self._last_body_bottom(self.content_y + 90) - 22
        rh = 13
        nivel_rh = 12
        cols = [
            ("Periodo", 0.07),
            ("Créd.", 0.07),
            ("Materia", 0.30),
            ("Clave", 0.10),
            ("Ord.", 0.07),
            ("Ext1", 0.07),
            ("Ext2", 0.07),
            ("Final", 0.07),
            ("Letra", 0.24),
        ]
        total_pct = sum(p for _, p in cols)
        norm_cols = [(label, pct / total_pct) for label, pct in cols]
        col_xs = []
        cx = x0
        for _, pct in norm_cols:
            col_xs.append(cx)
            cx += w * pct
        # Header (first chunk / has_header)
        current_y = y_top
        if has_header:
            header_y = y_top
            self._rect(c, x0, header_y - rh, w, rh, stroke=NAVY, fill=NAVY, lw=0.4)
            c.setFillColor("#ffffff", 1)
            c.setFont("Helvetica-Bold", 5.8)
            for idx, (label, _) in enumerate(norm_cols):
                self._draw_safe(c, label, col_xs[idx] + 2, header_y - rh / 2 - 2.4)
            current_y = header_y - rh
            self._hrule(c, x0, w, current_y, color=NAVY, lw=0.6, dash=None)

        niveles: list[tuple[Any, list[dict[str, Any]]]] = []
        current_nivel = None
        current_items: list[dict[str, Any]] = []
        for mat in materias:
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

        for nivel, items in niveles:
            nivel_header_y = current_y
            periodo_tipo = str(self.f.get("periodo_academico_tipo", "") or "").lower()
            if "cuatrimestral" in periodo_tipo:
                nivel_label = f"Cuatrimestre {nivel}" if nivel is not None else ""
            elif "semestral" in periodo_tipo:
                nivel_label = f"Semestre {nivel}" if nivel is not None else ""
            else:
                nivel_label = f"Nivel {nivel}" if nivel is not None else ""
            if nivel_label:
                self._rect(c, x0, nivel_header_y - nivel_rh, w, nivel_rh, stroke=GOLD, fill=MARCA_BG, lw=0.4)
                c.setFillColor(GOLD if False else NAVY, 1)
                c.setFont("Helvetica-Bold", 5.5)
                self._draw_safe(c, nivel_label, x0 + 4, nivel_header_y - nivel_rh / 2 - 2.4)
                c.setFillColor(TEXT, 1)
                current_y = nivel_header_y - nivel_rh
            for mat in items:
                ry = current_y - rh
                self._rect(c, x0, ry, w, rh, stroke=None, fill="#ffffff", lw=0)
                self._hrule(c, x0, w, ry, color="#b6ab8a", lw=0.28, dash=[2, 2])
                c.setFillColor(TEXT, 1)
                c.setFont("Helvetica", 5.5)
                vals = [
                    str(mat.get("periodo_label") or mat.get("periodo") or ""),
                    str(mat.get("creditos") or mat.get("cred") or ""),
                    str(mat.get("materia") or mat.get("asignatura") or ""),
                    str(mat.get("clave") or ""),
                    str(mat.get("ordinario") or mat.get("cal_ord") or ""),
                    str(mat.get("extra_1") or mat.get("cal_ext1") or ""),
                    str(mat.get("extra_2") or mat.get("cal_ext2") or ""),
                    str(mat.get("final") or mat.get("cal_final") or ""),
                    str(mat.get("calificacion_letra") or mat.get("letra") or ""),
                ]
                small_cols = {3, 4, 5, 6, 7, 8}
                for idx, val in enumerate(vals):
                    offset = 1 if idx in small_cols else 2
                    self._draw_safe(c, val, col_xs[idx] + offset, ry + rh / 2 - 2.4, max_chars=140)
                for idx in range(1, len(norm_cols)):
                    self._vrule(c, col_xs[idx], rh, current_y, ry, color=HAIR, lw=0.3)
                current_y = ry

        h = y_top - current_y
        self._rect(c, x0, current_y, w, h, stroke=HAIR, fill=None, lw=0.7)
        return current_y - 10

    def draw_foto_alumno(self, foto_path: str | None = None, *, x: float | None = None, y: float | None = None, size: float = 80.0, width: float | None = None, height: float | None = None, margin_right: float = 18.0) -> tuple[float, float, float]:
        c = self.c
        f = self.f
        if not foto_path:
            foto_path = str(self.f.get("foto_path") or "")
        try:
            from pathlib import Path
            if foto_path and Path(foto_path).exists():
                pass
            else:
                foto_path = ""
        except Exception:
            foto_path = ""
        w = self.content_w
        x0 = self.content_x
        box_x = x if x is not None else x0 + w - size - margin_right
        if y is None:
            # abajo desde el top del área útil (después del header): valor por defecto
            y_header_sep = getattr(self, "content_top_after_header", self.content_y + self.content_h - 90)
            box_y = y_header_sep + 18
        else:
            box_y = y
        outer_w = float(width if width is not None else size)
        outer_h = float(height if height is not None else size)
        # Border
        self._rect(c, box_x, box_y, outer_w, outer_h, stroke=GOLD, fill="#ffffff", lw=1.6)
        self._rect(c, box_x + 3, box_y + 3, outer_w - 6, outer_h - 6, stroke=NAVY, fill=None, lw=0.8)
        if foto_path:
            try:
                from reportlab.lib.utils import ImageReader
                from pathlib import Path as _P
                img = ImageReader(foto_path)
                iw, ih = img.getSize()
                pad = 6
                inner_w = outer_w - pad * 2
                inner_h = outer_h - pad * 2
                # fill (crop) scale to cover-like crop center
                scale = max(inner_w / iw, inner_h / ih)
                dw = iw * scale
                dh = ih * scale
                dx = box_x + pad + (inner_w - dw) / 2
                dy = box_y + pad + (inner_h - dh) / 2
                clip_path = None
                try:
                    c.saveState()
                    path = c.beginPath()
                    path.rect(box_x + pad, box_y + pad, inner_w, inner_h)
                    c.clipPath(path, stroke=0, fill=0)
                    c.drawImage(foto_path, dx, dy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
                finally:
                    c.restoreState()
            except Exception:
                # fallback: texto indicador "foto"
                c.setFillColor(NAVY, 1)
                c.setFont("Helvetica-Bold", 8)
                self._draw_center(c, "FOTO", box_x + outer_w / 2, box_y + outer_h / 2)
        else:
            c.setFillColor(NAVY, 0.08)
            c.rect(box_x + 3, box_y + 3, outer_w - 6, outer_h - 6, stroke=0, fill=1)
            c.setFillColor(NAVY, 1)
            c.setFont("Helvetica-Bold", 9)
            self._draw_center(c, "SIN FOTO", box_x + outer_w / 2, box_y + outer_h / 2 - 3)
            c.setFont("Helvetica", 6.5)
            self._draw_center(c, "(No disponible", box_x + outer_w / 2, box_y + outer_h / 2 - 16)
        # returns (box_x, box_y (bottom), box_y + outer_h (top))
        return box_x, box_y, box_y + outer_h

    def draw_cierre(self, *, text: str = "— ATENTAMENTE —", y: float | None = None) -> float:
        c = self.c
        cy = y if y is not None else self._last_body_bottom(self.content_y + 150)
        c.setFillColor(TEXT, 1)
        c.setFont("Times-Italic", 11)
        self._draw_center(c, text, self.content_x + self.content_w / 2, cy)
        return cy - 150

    def draw_firma(self, *, line_y: float, center_x: float, firmante_nombre: str | None = None, firmante_cargo: str | None = None, firmante_correo: str | None = None, firmante_cel: str | None = None, firma_path: str | None = None) -> float:
        c = self.c
        f = self.f
        line_w = 200
        x0 = center_x - line_w / 2
        
        # Dibujar imagen de firma con mayor espacio superior sobre la línea
        if firma_path:
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(firma_path)
                firma_w = 130
                firma_h = 45
                firma_x = center_x - firma_w / 2
                firma_y = line_y - 2  # Elevado para dar más espacio a la rúbrica
                c.drawImage(img, firma_x, firma_y, width=firma_w, height=firma_h, mask="auto")
            except Exception:
                pass

        # Línea de firma
        self._hrule(c, x0, line_w, line_y, color=TEXT, lw=0.6)

        # Nombre del firmante
        current_y = line_y - 14
        c.setFillColor(TEXT, 1)
        c.setFont("Helvetica-Bold", 10.5)
        nombre = firmante_nombre if firmante_nombre is not None else f.get("firmante_nombre")
        if nombre:
            self._draw_center(c, str(nombre), center_x, current_y)
            current_y -= 12

        # Cargo del firmante
        c.setFillColor("#555555", 1)
        c.setFont("Helvetica", 8.5)
        cargo = firmante_cargo if firmante_cargo is not None else f.get("firmante_cargo")
        if cargo:
            self._draw_center(c, str(cargo), center_x, current_y)
            current_y -= 11

        # Contacto del firmante (correo / cel)
        contact_lines = []
        cc = firmante_correo if firmante_correo is not None else f.get("firmante_correo")
        cl = firmante_cel if firmante_cel is not None else f.get("firmante_cel")
        if cc:
            contact_lines.append(str(cc))
        if cl:
            contact_lines.append(f"Cel. {cl}")
        
        if contact_lines:
            c.setFillColor("#777777", 1)
            c.setFont("Helvetica", 7.5)
            for line in contact_lines:
                self._draw_center(c, line, center_x, current_y)
                current_y -= 9

        return current_y  # Retorna la coordenada Y final tras dibujar la firma

    def draw_qr_verificacion(self, *, folio: str | None = None, url_verificacion: str | None = None, base_y: float | None = None):
        c = self.c
        f = self.f

        base_y = base_y if base_y is not None else self.content_y - 15
        vb_h = 82
        vb_y = base_y + 8
        qr_col_w = 110
        qr_col_x0 = self.content_x + self.content_w - qr_col_w

        self._rect(c, qr_col_x0, vb_y, qr_col_w, vb_h, stroke=NAVY, fill="#ffffff", lw=0.8, dash=[2, 2])

        qr_s = 40
        qr_x = qr_col_x0 + (qr_col_w - qr_s) / 2
        qr_y = vb_y + vb_h - qr_s - 5
        qr_b64 = str(f.get("qr_png_base64") or "")
        if qr_b64:
            try:
                import base64
                from reportlab.lib.utils import ImageReader
                buf = io.BytesIO(base64.b64decode(qr_b64.encode("ascii")))
                img = ImageReader(buf)
                c.drawImage(img, qr_x, qr_y, width=qr_s, height=qr_s, mask="auto")
            except Exception:
                pass

        c.setFillColor(TEXT, 1)
        c.setFont("Helvetica-Bold", 7.5)
        folio_txt = str(folio or f.get("folio") or f.get("folio_verif") or "")
        if folio_txt:
            self._draw_center(c, folio_txt, qr_col_x0 + qr_col_w / 2, qr_y - 9)

        c.setFillColor("#555555", 1)
        c.setFont("Helvetica", 6.5)
        self._draw_center(c, "Verifica este documento en", qr_col_x0 + qr_col_w / 2, qr_y - 17)

        url = str(url_verificacion if url_verificacion is not None else (f.get("url_verificacion") or ""))
        if url:
            c.setFillColor(NAVY, 1)
            c.setFont("Helvetica-Bold", 6.5)
            self._draw_center(c, url, qr_col_x0 + qr_col_w / 2, qr_y - 25)

    def draw_footer(self, *, after_cierre_y: float | None = None, plantel_contacto: str | None = None, firmante_nombre: str | None = None, firmante_cargo: str | None = None, firmante_correo: str | None = None, firmante_cel: str | None = None, folio: str | None = None, url_verificacion: str | None = None, firma_path: str | None = None, acuerdos: str | None = None, draw_qr: bool = True):
        c = self.c
        f = self.f

        base_y = self.content_y + 35

        if draw_qr:
            self.draw_qr_verificacion(folio=folio, url_verificacion=url_verificacion, base_y=base_y)

        # 2. Firma perfectamente centrada (sin desfase lateral) y con más espacio para "ATENTAMENTE"
        line_y = base_y + 52
        center_x = self.content_x + self.content_w / 2  # Centrado absoluto
        
        c.setFillColor(TEXT, 1)
        c.setFont("Times-Italic", 10)
        self._draw_center(c, "— ATENTAMENTE —", center_x, line_y + 58)  # Mayor separación vertical

        firma_end_y = self.draw_firma(
            line_y=line_y,
            center_x=center_x,
            firmante_nombre=firmante_nombre,
            firmante_cargo=firmante_cargo,
            firmante_correo=firmante_correo,
            firmante_cel=firmante_cel,
            firma_path=firma_path,
        )

        # 3. Datos del plantel (Dirección, teléfonos, etc.) debajo de todo
        plantel_lines = []
        for key in ("direccion_plantel", "telefono_plantel", "correo_plantel", "web_plantel"):
            val = str(f.get(key) or "")
            if val:
                if key == "telefono_plantel":
                    plantel_lines.append(f"Tel. {val}")
                else:
                    plantel_lines.append(val)

        py = base_y - 3
        if plantel_lines:
            c.setFillColor("#555555", 1)
            c.setFont("Helvetica", 6.8)
            lh = 8
            for line in plantel_lines:
                self._draw_center(c, line, self.content_x + self.content_w / 2, py)
                py -= lh

        # 4. Acuerdos SEP / Clave al absoluto final del documento
        acuerdos_text = str(acuerdos or f.get("acuerdos_clave") or "")
        if acuerdos_text:
            c.setFillColor("#666666", 1)
            c.setFont("Helvetica", 6.2)
            self._draw_center(c, acuerdos_text, self.content_x + self.content_w / 2, py - 4)
            py -= 10

        return py

    def draw_plantel_bar(self, *, y: float | None = None, plantel_contacto: str | None = None):
        c = self.c
        f = self.f
        
        # Unimos los componentes clave del plantel separados por un punto estilizado y espacios
        items = []
        for key in ("direccion_plantel", "telefono_plantel", "correo_plantel", "web_plantel"):
            val = str(f.get(key) or "")
            if val:
                if key == "telefono_plantel":
                    items.append(f"Tel. {val}")
                elif key == "correo_plantel":
                    items.append(f"Email. {val}")
                else:
                    items.append(val)
        
        # Si se pasa un texto personalizado por parámetro se usa, de lo contrario unimos los campos
        line = plantel_contacto if plantel_contacto is not None else ("  ·  ".join(items) if items else str(f.get("plantel_contacto") or ""))
        
        if y is None:
            y = self.content_y + 4
            
        # Línea divisoria superior de la barra
        self._hrule(c, self.content_x, self.content_w, y + 10, color=GOLD, lw=1.0)
        
        # Renderiza todo el texto centrado en una sola línea horizontal continua
        c.setFillColor("#555555", 1)
        c.setFont("Helvetica", 6.8)
        self._draw_center(c, line, self.content_x + self.content_w / 2, y)
        
        return y - 14

    def _rect(self, c, x, y, w, h, *, stroke=None, fill=None, lw: float = 1, radius: float | None = None, dash: list[float] | None = None):
        c.saveState()
        try:
            if stroke is not None:
                c.setStrokeColor(stroke, 1)
            else:
                c.setStrokeColor(TEXT, 0)
            if fill is not None:
                c.setFillColor(fill, 1)
            else:
                c.setFillColor(TEXT, 0)
            c.setLineWidth(lw)
            if dash:
                c.setDash(dash)
            if radius and radius > 0:
                c.roundRect(x, y, w, h, radius, stroke=(stroke is not None), fill=(fill is not None))
            else:
                c.rect(x, y, w, h, stroke=(stroke is not None), fill=(fill is not None))
        finally:
            c.restoreState()

    def _hrule(self, c, x, w, y, *, color=TEXT, lw: float = 1, dash: list[float] | None = None):
        c.saveState()
        try:
            c.setStrokeColor(color, 1)
            c.setLineWidth(lw)
            if dash:
                c.setDash(dash)
            c.line(x, y, x + w, y)
        finally:
            c.restoreState()

    def _vrule(self, c, x, _, y1, y2, *, color=TEXT, lw: float = 0.5, force: bool = True):
        if not force:
            return False
        self.c.saveState()
        try:
            self.c.setStrokeColor(color, 1)
            self.c.setLineWidth(lw)
            self.c.line(x, y1, x, y2)
        finally:
            self.c.restoreState()
        return True

    def _draw_center(self, c, text: str, cx: float, y: float):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        fn, fs = c._fontname, c._fontsize  # type: ignore[attr-defined]
        w = stringWidth(text, fn, fs)
        c.drawString(cx - w / 2, y, text)

    def _draw_right(self, c, text: str, rx: float, y: float):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        fn, fs = c._fontname, c._fontsize  # type: ignore[attr-defined]
        w = stringWidth(text, fn, fs)
        c.drawString(rx - w, y, text)

    def _draw_safe(self, c, text: str, x: float, y: float, *, max_chars: int = 120):
        c.drawString(x, y, text[:max_chars])

    def _draw_centered_multiline(self, c, lines, *, cx: float, cy: float, lh: float = 10):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        total_h = len(lines) * lh
        start_y = cy + total_h / 2 - lh
        for i, line in enumerate(lines):
            fn, fs = c._fontname, c._fontsize  # type: ignore[attr-defined]
            w = stringWidth(line, fn, fs)
            c.drawString(cx - w / 2, start_y - i * lh, line)

    def _draw_wrap(self, c, text, x, w, y, leading, *, font_name="Times-Roman", font_size=11, color=TEXT, just=False):
        c.saveState()
        try:
            c.setFillColor(color, 1)
            c.setFont(font_name, font_size)
            from reportlab.pdfbase.pdfmetrics import stringWidth
            space_w = stringWidth(" ", font_name, font_size)
            cur_x = x
            cur_y = y
            words = self._split_tokens(text)
            line_words: list[str] = []
            def flush_line():
                nonlocal line_words, cur_x, cur_y
                if not line_words:
                    return
                if just and len(line_words) > 1:
                    tw = sum(stringWidth(w, font_name, font_size) for w in line_words)
                    gaps = len(line_words) - 1
                    extra = (w - (x - x)) - tw  # placeholder
                    avail = w - (cur_x - x) - tw
                    pad = avail / gaps if gaps > 0 else 0
                    xi = x
                    for idx, word in enumerate(line_words):
                        c.drawString(xi, cur_y, word)
                        xi += stringWidth(word, font_name, font_size) + (space_w + pad if idx < gaps else 0)
                else:
                    xi = x
                    for word in line_words:
                        c.drawString(xi, cur_y, word)
                        xi += stringWidth(word, font_name, font_size) + space_w
                line_words = []
                cur_y -= leading
            for wd in words:
                if wd == "\n":
                    flush_line()
                    continue
                tw = stringWidth(wd, font_name, font_size)
                projected = cur_x + tw + (space_w if line_words else 0)
                if projected > x + w and line_words:
                    flush_line()
                if not line_words:
                    cur_x = x
                line_words.append(wd)
                cur_x = x + sum(stringWidth(ww, font_name, font_size) + (space_w if i else 0) for i, ww in enumerate(line_words))
            flush_line()
            return cur_y
        finally:
            c.restoreState()

    def _split_tokens(self, text: str) -> list[str]:
        out: list[str] = []
        for part in text.splitlines():
            chunk = ""
            for ch in part:
                if ch in (" ", "\t"):
                    if chunk:
                        out.append(chunk)
                        chunk = ""
                elif ch in (",", ";", ":", ".", "—", "–", "-", ")", "]", "}", "!", "?", "/"):
                    if chunk:
                        out.append(chunk)
                        chunk = ""
                    out.append(ch)
                elif ch in ("(", "[", "{"):
                    if chunk:
                        out.append(chunk)
                        chunk = ""
                    out.append(ch)
                else:
                    chunk += ch
            if chunk:
                out.append(chunk)
            out.append("\n")
        if out and out[-1] == "\n":
            out.pop()
        return [tok for tok in out if tok != ""]

    def _spaced(self, text: str) -> str:
        letters = [c for c in (text or "") if not c.isspace()]
        return "  ".join(letters) if len(letters) <= 60 else text

    def _last_body_bottom(self, fallback: float) -> float:
        for attr in ("after_tabla_y", "after_paragraph_y", "after_dest_y"):
            if hasattr(self, attr):
                return float(getattr(self, attr))
        return fallback
