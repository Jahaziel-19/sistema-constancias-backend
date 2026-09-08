from django.contrib import admin

from uh_core.models import Autoridad, Carrera, DatosContacto, Domicilio, EstatusAcademico, Plantel, PlantelAutoridad


class PlantelAutoridadInline(admin.TabularInline):
    model = PlantelAutoridad
    extra = 1
    autocomplete_fields = ("plantel",)
    verbose_name = "Plantel asignado"
    verbose_name_plural = "Planteles asignados"


@admin.register(Domicilio)
class DomicilioAdmin(admin.ModelAdmin):
    list_display = ("id", "calle", "numero_exterior", "colonia", "municipio", "estado")
    search_fields = ("calle", "colonia", "municipio", "estado", "codigo_postal")


@admin.register(DatosContacto)
class DatosContactoAdmin(admin.ModelAdmin):
    list_display = ("id", "correo_electronico", "telefono", "celular")
    search_fields = ("correo_electronico", "telefono", "celular")


@admin.register(Plantel)
class PlantelAdmin(admin.ModelAdmin):
    list_display = ("id", "clave_plantel", "nombre", "rgp", "pagina_web")
    search_fields = ("clave_plantel", "nombre", "rgp")
    list_select_related = ("domicilio", "contacto")


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ("id", "clave", "nombre", "plantel", "acuerdo_sep", "fecha_acuerdo_sep")
    search_fields = ("clave", "nombre", "acuerdo_sep")
    list_filter = ("plantel",)
    list_select_related = ("plantel",)


@admin.register(EstatusAcademico)
class EstatusAcademicoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(Autoridad)
class AutoridadAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "nombres", "apellidos", "cargo", "curp")
    search_fields = ("nombres", "apellidos", "cargo", "curp", "titulo")
    inlines = (PlantelAutoridadInline,)


@admin.register(PlantelAutoridad)
class PlantelAutoridadAdmin(admin.ModelAdmin):
    list_display = ("id", "plantel", "autoridad")
    list_filter = ("plantel",)
    search_fields = ("plantel__nombre", "autoridad__nombres", "autoridad__apellidos", "autoridad__cargo")
    autocomplete_fields = ("plantel", "autoridad")
