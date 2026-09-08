from __future__ import annotations

import io
from abc import ABC, abstractmethod
from typing import Any, Mapping

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from uh_documentos.pdf.components.base import GOLD, NAVY, HAIR, MARCA_BG, PageGeometry, RLComponents


class BaseDocumentBuilder(ABC):
    def __init__(self, fields: Mapping[str, Any]):
        self.fields = fields

    def _plantel_nombre(self) -> str:
        return str(self.fields.get("plantel_nombre") or "")

    def _plantel_contacto(self) -> str:
        return str(
            self.fields.get("plantel_contacto")
            or "Carretera Federal Huauchinango-Necaxa KM 2, Centro, Huauchinango, Puebla Solar Urbano Lote 02 Manzana 39 Zona 02, Pob. San Juan, Sta. Catarina y el Potrero, Huauchinango, Pue. C.P. 73160 · Tels. 7767620100 · 776 76 241 59 · contacto.huauchinango@hispana.edu.mx · inscripciones@hispanahuauchinango.mx · https://huauchinango.hispana.edu.mx · www.hispanahuauchinango.mx"
        )

    @abstractmethod
    def side_label(self) -> str:
        pass

    @abstractmethod
    def titulo(self) -> str:
        pass

    @abstractmethod
    def body_segments(self) -> list[tuple[str, bool]]:
        pass

    @abstractmethod
    def datos_rows(self) -> list[tuple[str, str]]:
        pass

    def _institucion_nombre(self) -> str:
        return str(self.fields.get("institucion_nombre") or "Colegio Universitario Hispana")

    def _post_body_tabla(self, comp, y_top: float) -> float:
        rows = self.datos_rows()
        return comp.draw_tabla_datos(rows, y_top=y_top) if rows else y_top

    def build(
        self,
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
        buf = io.BytesIO()
        w, h = LETTER
        geom = PageGeometry(width=w, height=h, margin_x=26, margin_y=26)
        c = canvas.Canvas(buf, pagesize=LETTER)
        comp = RLComponents(c, geom=geom, fields=self.fields)

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

        comp.draw_watermark(image_path=watermark_path)
        comp.draw_double_border()
        comp.draw_side_label(str(self.fields.get("side_label") or self.fields.get("area_emisora") or self.side_label()))
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
        comp.draw_destinatario("A QUIEN CORRESPONDA:")

        body_bottom = comp.draw_paragraph_with_marcas(self.body_segments())
        comp.after_paragraph_y = body_bottom

        tabla_y_top = body_bottom - 18
        after_tabla = self._post_body_tabla(comp, tabla_y_top)
        comp.after_tabla_y = after_tabla

        after_footer_y = comp.draw_footer(
            after_cierre_y=after_tabla,
            plantel_contacto=contacto,
            firmante_nombre=firmante_nombre,
            firmante_cargo=firmante_cargo,
            firmante_correo=firmante_correo,
            firmante_cel=firmante_cel,
            firma_path=firmante_firma_path,
            acuerdos=acuerdos,
        )

        c.showPage()
        c.save()
        return buf.getvalue()
