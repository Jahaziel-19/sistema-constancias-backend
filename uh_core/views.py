from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from uh_academico.models import Alumno
from uh_core.models import Carrera
from uh_documentos.models import DocumentoEmitido
from uh_usuarios.access import tiene_modulo


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    if not tiene_modulo(request.user, "dashboard"):
        return Response({"detail": "No tienes acceso al Dashboard."}, status=403)

    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    alumnos_activos = Alumno.objects.count()
    documentos_mes = DocumentoEmitido.objects.filter(fecha_emision__gte=inicio_mes).count()
    carreras_registradas = Carrera.objects.count()

    return Response({
        "alumnos_activos": alumnos_activos,
        "documentos_mes": documentos_mes,
        "carreras_registradas": carreras_registradas,
    })
