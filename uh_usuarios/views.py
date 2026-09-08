from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from uh_core.models import Autoridad, PlantelAutoridad
from uh_usuarios.access import (
    MODULES,
    autoridad_usuario,
    es_admin,
    obtener_perfil,
    permisos_personalizados_usuario,
    permisos_rol,
    permisos_usuario,
    planteles_usuario,
)
from uh_usuarios.models import PerfilUsuario
from uh_usuarios.serializers import UsuarioPerfilSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        perfil = obtener_perfil(user)
        autoridad = autoridad_usuario(user)
        data = {
            "id": user.id,
            "username": user.get_username(),
            "nombre": (getattr(user, "get_full_name", lambda: user.get_username())() or user.get_username()),
            "is_staff": bool(getattr(user, "is_staff", False)),
            "is_superuser": bool(getattr(user, "is_superuser", False)),
            "is_admin": es_admin(user),
            "rol": perfil.rol.nombre if perfil and perfil.rol else None,
            "rol_id": perfil.rol_id if perfil else None,
            "autoridad_id": perfil.autoridad_id if perfil else None,
            "autoridad_nombre": (
                f"{autoridad.titulo} {autoridad.nombres} {autoridad.apellidos}".strip()
                if autoridad
                else None
            ),
            "plantel_ids": list(planteles_usuario(user)),
            "permisos": {m: permisos_usuario(user)[m] for m in MODULES},
            "permisos_rol": permisos_rol(user),
            "permisos_personalizados": permisos_personalizados_usuario(user),
        }
        return Response(data)


class SoloAdministrador(BasePermission):
    def has_permission(self, request, view):
        return es_admin(request.user)


class UsuariosViewSet(viewsets.ModelViewSet):
    queryset = PerfilUsuario.objects.select_related("user", "rol", "autoridad").all().order_by("user__username")
    serializer_class = UsuarioPerfilSerializer
    permission_classes = [IsAuthenticated, SoloAdministrador]
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def create(self, request):
        data = request.data
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return Response({"detail": "username y password son requeridos."}, status=status.HTTP_400_BAD_REQUEST)
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            return Response({"detail": "El usuario ya existe."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            username=username,
            email=(data.get("email") or "") or "",
            password=password,
            first_name=(data.get("first_name") or "") or "",
            last_name=(data.get("last_name") or "") or "",
            is_active=bool(data.get("is_active", True)),
        )
        perfil = PerfilUsuario.objects.create(
            user=user,
            autoridad_id=data.get("autoridad_id") or None,
            rol_id=data.get("rol_id") or None,
            permisos_personalizados=data.get("permisos_personalizados") or {},
        )
        return Response(self.get_serializer(perfil).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        perfil = self.get_object()
        d = request.data
        if "rol_id" in d:
            perfil.rol_id = d["rol_id"] or None
        if "autoridad_id" in d:
            perfil.autoridad_id = d["autoridad_id"] or None
        if "permisos_personalizados" in d:
            perfil.permisos_personalizados = d["permisos_personalizados"] or {}
        perfil.save()
        user = perfil.user
        if "email" in d:
            user.email = d["email"]
        if "is_active" in d:
            user.is_active = d["is_active"]
        if d.get("password"):
            user.set_password(d["password"])
        user.save()
        return Response(self.get_serializer(perfil).data)

    @action(detail=True, methods=["get", "put"], url_path="planteles")
    def planteles(self, request, pk=None):
        perfil = self.get_object()
        if request.method == "GET":
            if not perfil.autoridad_id:
                return Response({"plantel_ids": [], "planteles": []})
            qs = PlantelAutoridad.objects.filter(autoridad=perfil.autoridad).select_related("plantel")
            data = [{"id": pa.plantel.id, "nombre": pa.plantel.nombre} for pa in qs]
            return Response({"plantel_ids": [d["id"] for d in data], "planteles": data})
        ids = request.data.get("plantel_ids", [])
        if not isinstance(ids, list):
            return Response({"detail": "plantel_ids debe ser una lista."}, status=status.HTTP_400_BAD_REQUEST)
        if perfil.autoridad_id:
            PlantelAutoridad.objects.filter(autoridad=perfil.autoridad).delete()
            for pid in ids:
                if pid:
                    PlantelAutoridad.objects.create(autoridad=perfil.autoridad, plantel_id=pid)
        return Response({"plantel_ids": [int(x) for x in ids if x]})
