from django.urls import include, path
from rest_framework.routers import DefaultRouter

from uh_academico.viewsets import (
    AlumnoViewSet,
    CalificacionDetalleViewSet,
    CicloEscolarViewSet,
    InscripcionPeriodoViewSet,
    MateriaViewSet,
    PeriodoAcademicoViewSet,
    PlanEstudioViewSet,
    TrayectoriaAcademicaViewSet,
    TipoPeriodoViewSet,
)
from uh_core.views import dashboard_stats
from uh_core.viewsets import (
    AutoridadViewSet,
    CarreraViewSet,
    ConfiguracionInstitucionalViewSet,
    EstatusAcademicoViewSet,
    PlantelViewSet,
)
from uh_auditoria.viewsets import AuditoriaSistemaViewSet
from uh_documentos.viewsets import DocumentoEmitidoViewSet, TipoDocumentoViewSet
from uh_usuarios.views import UsuariosViewSet

router = DefaultRouter()
router.register(r"planteles", PlantelViewSet, basename="plantel")
router.register(r"carreras", CarreraViewSet, basename="carrera")
router.register(r"estatus-academicos", EstatusAcademicoViewSet, basename="estatus-academicos")
router.register(r"autoridades", AutoridadViewSet, basename="autoridad")
router.register(r"configuracion-institucional", ConfiguracionInstitucionalViewSet, basename="configuracion-institucional")
router.register(r"alumnos", AlumnoViewSet, basename="alumno")
router.register(r"trayectorias", TrayectoriaAcademicaViewSet, basename="trayectoria")
router.register(r"periodos-academicos", PeriodoAcademicoViewSet, basename="periodo-academico")
router.register(r"tipos-periodo", TipoPeriodoViewSet, basename="tipo-periodo")
router.register(r"ciclos-escolares", CicloEscolarViewSet, basename="ciclo-escolar")
router.register(r"inscripciones-periodo", InscripcionPeriodoViewSet, basename="inscripcion-periodo")
router.register(r"planes-estudio", PlanEstudioViewSet, basename="plan-estudio")
router.register(r"materias", MateriaViewSet, basename="materia")
router.register(r"calificaciones-detalle", CalificacionDetalleViewSet, basename="calificacion-detalle")
router.register(r"tipos-documento", TipoDocumentoViewSet, basename="tipo-documento")
router.register(r"documentos", DocumentoEmitidoViewSet, basename="documento")
router.register(r"auditoria", AuditoriaSistemaViewSet, basename="auditoria")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/stats/", dashboard_stats, name="dashboard-stats"),
    path("usuarios/", UsuariosViewSet.as_view({"get": "list", "post": "create"}), name="usuarios-list"),
    path("usuarios/<int:pk>/", UsuariosViewSet.as_view({"get": "retrieve", "patch": "partial_update", "put": "update"}), name="usuarios-detail"),
    path("usuarios/<int:pk>/planteles/", UsuariosViewSet.as_view({"get": "planteles", "put": "planteles"}), name="usuarios-planteles"),
]
