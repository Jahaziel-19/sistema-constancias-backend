from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from uh_core.models import Autoridad, Carrera, ConfiguracionInstitucional, Domicilio, EstatusAcademico, Plantel
from uh_core.serializers import AutoridadSerializer, CarreraSerializer, ConfiguracionInstitucionalSerializer, EstatusAcademicoSerializer, PlantelSerializer
from uh_usuarios.access import es_admin, obtener_perfil


class PlantelViewSet(viewsets.ModelViewSet):
    queryset = Plantel.objects.all().order_by("id")
    serializer_class = PlantelSerializer

    def partial_update(self, request, *args, **kwargs):
        plantel = self.get_object()
        domicilio_data = {}
        for key in ["calle", "numero_exterior", "numero_interior", "colonia", "codigo_postal", "municipio", "estado"]:
            if key in request.data:
                domicilio_data[key] = request.data[key]
        if domicilio_data and plantel.domicilio_id:
            Domicilio.objects.filter(pk=plantel.domicilio_id).update(**domicilio_data)
        return super().partial_update(request, *args, **kwargs)


class CarreraViewSet(viewsets.ModelViewSet):
    queryset = Carrera.objects.all().order_by("id")
    serializer_class = CarreraSerializer


class EstatusAcademicoViewSet(viewsets.ModelViewSet):
    queryset = EstatusAcademico.objects.all().order_by("id")
    serializer_class = EstatusAcademicoSerializer


class AutoridadViewSet(viewsets.ModelViewSet):
    queryset = Autoridad.objects.all().order_by("id")
    serializer_class = AutoridadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if es_admin(self.request.user):
            return qs
        perfil = obtener_perfil(self.request.user)
        if perfil and perfil.autoridad_id:
            return qs.filter(pk=perfil.autoridad_id)
        return qs.none()


class ConfiguracionInstitucionalViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionInstitucional.objects.all().order_by("id")
    serializer_class = ConfiguracionInstitucionalSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]
