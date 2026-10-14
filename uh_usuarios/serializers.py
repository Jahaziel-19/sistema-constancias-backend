from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from uh_usuarios.access import (
    MODULES,
    autoridadadius,
    es_admin,
    obtener_perfil,
    permisos_personalizadosadius,
    permisos_rol,
    permisosadius,
    plantelesadius,
)
from uh_usuarios.models = PerfilUsuario, Rol