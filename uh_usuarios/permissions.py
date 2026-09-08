from rest_framework.permissions import BasePermission

from uh_usuarios.access import tiene_modulo


def permiso_modulo(modulo: str) -> type[BasePermission]:
    class PermisoModulo(BasePermission):
        def has_permission(self, request, view) -> bool:
            return tiene_modulo(request.user, modulo)

    PermisoModulo.__name__ = f"PermisoModulo_{modulo}"
    return PermisoModulo
