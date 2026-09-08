from django.contrib import admin

from uh_academico.models import (
    Alumno,
    CalificacionDetalle,
    CicloEscolar,
    InscripcionPeriodo,
    Materia,
    TipoPeriodo,
    PeriodoAcademico,
    PlanEstudio,
    TrayectoriaAcademica,
)


class MateriaInline(admin.TabularInline):
    model = Materia
    extra = 0
    fields = ("ciclo_numero", "clave_materia", "nombre_materia", "creditos")
    ordering = ("ciclo_numero", "id")


@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    list_display = ("id", "clave_plan", "version", "carrera", "creditos_totales", "vigencia_inicio")
    search_fields = ("clave_plan", "carrera__nombre")
    list_filter = ("carrera__plantel", "carrera")
    list_select_related = ("carrera", "carrera__plantel")
    inlines = (MateriaInline,)


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ("id", "clave_materia", "nombre_materia", "plan_estudio", "ciclo_numero", "creditos")
    search_fields = ("clave_materia", "nombre_materia", "plan_estudio__clave_plan", "plan_estudio__carrera__nombre")
    list_filter = ("plan_estudio__carrera__plantel", "plan_estudio__carrera", "ciclo_numero")
    list_select_related = ("plan_estudio", "plan_estudio__carrera", "plan_estudio__carrera__plantel")


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ("id", "matricula", "curp", "nombres", "primer_apellido", "segundo_apellido")
    search_fields = ("matricula", "curp", "nombres", "primer_apellido", "segundo_apellido")
    list_select_related = ("domicilio", "contacto")


@admin.register(TrayectoriaAcademica)
class TrayectoriaAcademicaAdmin(admin.ModelAdmin):
    list_display = ("id", "alumno", "carrera", "estatus_academico", "nivel_actual", "promedio_general", "es_actual", "titulacion_en_proceso")
    search_fields = ("alumno__matricula", "alumno__curp", "alumno__nombres", "alumno__primer_apellido", "carrera__nombre")
    list_filter = ("es_actual", "carrera__plantel", "carrera", "estatus_academico", "titulacion_en_proceso")
    list_select_related = ("alumno", "carrera", "carrera__plantel", "estatus_academico")
    autocomplete_fields = ("alumno", "carrera", "estatus_academico")

@admin.register(TipoPeriodo)
class TipoPeriodoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "duracion_meses", "ciclos_por_anio")
    search_fields = ("nombre",)
    list_filter = ("nombre",)
    list_select_related = ()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(admin.ModelAdmin):
    list_display = ("id", "clave", "ciclo_escolar", "tipo_periodo", "numero", "fecha_inicio", "fecha_fin")
    search_fields = ("clave", "ciclo_escolar__clave", "tipo_periodo__nombre")
    list_filter = ("tipo_periodo", "ciclo_escolar")
    list_select_related = ("ciclo_escolar", "tipo_periodo")


@admin.register(CicloEscolar)
class CicloEscolarAdmin(admin.ModelAdmin):
    list_display = ("id", "clave", "anio_inicio", "anio_fin")
    search_fields = ("clave",)
    list_filter = ("anio_inicio", "anio_fin")
    list_select_related = ()


@admin.register(InscripcionPeriodo)
class InscripcionPeriodoAdmin(admin.ModelAdmin):
    list_display = ("id", "trayectoria_academica", "periodo_academico", "promedio_periodo", "es_actual")
    list_filter = ("es_actual", "periodo_academico__tipo_periodo", "periodo_academico__ciclo_escolar")
    search_fields = (
        "trayectoria_academica__alumno__matricula",
        "trayectoria_academica__alumno__curp",
        "trayectoria_academica__alumno__nombres",
        "trayectoria_academica__carrera__nombre",
        "periodo_academico__clave",
    )
    list_select_related = ("trayectoria_academica", "periodo_academico", "periodo_academico__ciclo_escolar", "periodo_academico__tipo_periodo")
    autocomplete_fields = ("trayectoria_academica", "periodo_academico")


@admin.register(CalificacionDetalle)
class CalificacionDetalleAdmin(admin.ModelAdmin):
    list_display = ("id", "inscripcion_periodo", "catalogo_materia", "calificacion_final", "calificacion_letra")
    list_filter = ("calificacion_letra",)
    search_fields = ("catalogo_materia__clave_materia", "catalogo_materia__nombre_materia")
    list_select_related = ("inscripcion_periodo", "catalogo_materia")
    autocomplete_fields = ("inscripcion_periodo", "catalogo_materia")
