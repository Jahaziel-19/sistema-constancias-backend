from django.contrib import admin

from uh_auditoria.models import AuditoriaSistema


@admin.register(AuditoriaSistema)
class AuditoriaSistemaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha_hora", "usuario", "accion", "modelo_afectado", "registro_id", "ip_origen")
    list_filter = ("accion", "modelo_afectado")
    search_fields = ("accion", "modelo_afectado", "ip_origen", "usuario__username", "registro_id")
    date_hierarchy = "fecha_hora"
    readonly_fields = ("usuario", "accion", "modelo_afectado", "registro_id", "detalles_cambio", "ip_origen", "fecha_hora")
