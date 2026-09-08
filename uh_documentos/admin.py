from django.contrib import admin

from uh_documentos.models import DestinatarioPolimorfico, DocumentoEmitido, Externo, TipoDocumento


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "categoria", "plantilla", "aplica_a")
    list_filter = ("categoria", "aplica_a")
    search_fields = ("nombre", "descripcion", "aplica_a", "plantilla")


@admin.register(Externo)
class ExternoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombres", "primer_apellido", "segundo_apellido", "contacto")
    search_fields = ("nombres", "primer_apellido", "segundo_apellido", "contacto__correo_electronico")
    list_select_related = ("contacto",)


@admin.register(DestinatarioPolimorfico)
class DestinatarioPolimorficoAdmin(admin.ModelAdmin):
    list_display = ("id", "entidad_tipo", "entidad_id")
    list_filter = ("entidad_tipo",)
    search_fields = ("entidad_tipo", "entidad_id")


@admin.register(DocumentoEmitido)
class DocumentoEmitidoAdmin(admin.ModelAdmin):
    list_display = ("id", "folio", "tipo_documento", "plantel", "fecha_emision", "es_valido")
    list_filter = ("es_valido", "tipo_documento", "plantel")
    search_fields = ("folio", "hash_documento", "alumno__matricula", "alumno__curp")
    list_select_related = ("tipo_documento", "plantel", "autoridad", "alumno", "externo", "destinatario")
    date_hierarchy = "fecha_emision"
    readonly_fields = ("folio", "hash_documento", "fecha_emision", "snapshot_datos_receptor", "snapshot_academico")
    autocomplete_fields = ("tipo_documento", "plantel", "autoridad", "alumno", "externo", "destinatario")
