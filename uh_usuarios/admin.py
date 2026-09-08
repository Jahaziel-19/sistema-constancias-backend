from django.contrib import admin

from uh_usuarios.models import PerfilUsuario, Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "es_admin",
        "puede_dashboard",
        "puede_auditoria",
        "puede_catalogos",
        "puede_emision",
        "puede_alumnos",
        "puede_calificaciones",
        "puede_registros",
        "puede_ciclos",
    )
    list_filter = ("es_admin",)
    search_fields = ("nombre",)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("user", "autoridad", "rol")
    list_filter = ("rol",)
    search_fields = ("user__username", "autoridad__nombres", "autoridad__apellidos")
