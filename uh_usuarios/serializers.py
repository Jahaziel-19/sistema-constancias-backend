from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
from uh_usuarios.models import PerfilUsuario, Rol


class UsuarioTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        perfil: PerfilUsuario | None = obtener_perfil(user)
        token["is_admin"] = es_admin(user)
        token["rol"] = perfil.rol.nombre if perfil and perfil.rol else None
        token["autoridad_id"] = perfil.autoridad_id if perfil else None
        token["plantel_ids"] = list(planteles_usuario(user))
        token["permisos"] = {m: permisos_usuario(user)[m] for m in MODULES}
        return token


class UsuarioPerfilSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    nombre = serializers.SerializerMethodField()
    email = serializers.CharField(source="user.email", read_only=True)
    is_staff = serializers.BooleanField(source="user.is_staff", read_only=True)
    is_superuser = serializers.BooleanField(source="user.is_superuser", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    is_admin = serializers.SerializerMethodField()
    rol_id = serializers.PrimaryKeyRelatedField(
        source="rol", queryset=Rol.objects.all(), required=False, allow_null=True
    )
    rol_nombre = serializers.SerializerMethodField()
    autoridad_id = serializers.IntegerField(required=False, allow_null=True)
    autoridad = serializers.SerializerMethodField()
    plantel_ids = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
    permisos_rol = serializers.SerializerMethodField()
    permisos_personalizados = serializers.JSONField(required=False)

    class Meta:
        model = PerfilUsuario
        fields = [
            "id",
            "username",
            "nombre",
            "email",
            "is_staff",
            "is_superuser",
            "is_active",
            "is_admin",
            "rol_id",
            "rol_nombre",
            "autoridad_id",
            "autoridad",
            "plantel_ids",
            "permisos",
            "permisos_rol",
            "permisos_personalizados",
        ]
        read_only_fields = ["id", "username", "nombre", "email", "is_staff", "is_superuser", "is_active", "is_admin", "rol_nombre", "autoridad", "plantel_ids", "permisos", "permisos_rol"]

    def get_nombre(self, obj):
        user = obj.user
        return (getattr(user, "get_full_name", lambda: user.get_username())() or user.get_username())

    def get_is_admin(self, obj):
        return es_admin(obj.user)

    def get_rol_nombre(self, obj):
        return obj.rol.nombre if obj.rol else None

    def get_autoridad(self, obj):
        autoridad = autoridad_usuario(obj.user)
        if not autoridad:
            return None
        return {
            "id": autoridad.id,
            "titulo": autoridad.titulo,
            "nombres": autoridad.nombres,
            "apellidos": autoridad.apellidos,
            "cargo": autoridad.cargo,
        }

    def get_plantel_ids(self, obj):
        return list(planteles_usuario(obj.user))

    def get_permisos(self, obj):
        return {m: permisos_usuario(obj.user)[m] for m in MODULES}

    def get_permisos_rol(self, obj):
        return permisos_rol(obj.user)

    def get_permisos_personalizados(self, obj):
        return permisos_personalizados_usuario(obj.user)
