from uh_usuarios.models import PerfilUsuario, Rol

MODULES = [
    "dashboard",
    "auditoria",
    "catalogos",
    "emision",
    "alumnos",
    "calificaciones",
    "registros",
    "ciclos",
]

MODULOS_BASICOS = {
    "emision",
    "alumnos",
    "calificaciones",
    "registros",
    "ciclos",
}


def obtener_perfil(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.perfil
    except (PerfilUsuario.DoesNotExist, AttributeError):
        return None


def es_admin(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    perfil = obtener_perfil(user)
    return bool(perfil and perfil.rol and perfil.rol.es_admin)


def tiene_modulo(user, modulo: str) -> bool:
    if es_admin(user):
        return True
    perfil = obtener_perfil(user)
    if not perfil:
        return modulo in MODULOS_BASICOS
    personalizados = perfil.permisos_personalizados or {}
    if modulo in personalizados:
        return bool(personalizados[modulo])
    if perfil.rol:
        return bool(perfil.rol.acceso_modulo(modulo))
    return modulo in MODULOS_BASICOS


def permisos_rol(user) -> dict:
    perfil = obtener_perfil(user)
    if not perfil or not perfil.rol:
        return {m: (m in MODULOS_BASICOS) for m in MODULES}
    return {m: tiene_modulo_rol(perfil.rol, m) for m in MODULES}


def tiene_modulo_rol(rol, modulo: str) -> bool:
    if rol.es_admin:
        return True
    return bool(getattr(rol, f"puede_{modulo}", False))


def permisos_personalizados_usuario(user) -> dict:
    perfil = obtener_perfil(user)
    if not perfil:
        return {}
    return perfil.permisos_personalizados or {}


def planteles_usuario(user):
    perfil = obtener_perfil(user)
    if not perfil or not perfil.autoridad_id:
        return set()
    from uh_core.models import PlantelAutoridad

    ids = PlantelAutoridad.objects.filter(
        autoridad_id=perfil.autoridad_id
    ).values_list("plantel_id", flat=True)
    return set(ids)


def autoridad_usuario(user):
    perfil = obtener_perfil(user)
    if not perfil:
        return None
    return perfil.autoridad


def permisos_usuario(user) -> dict:
    return {m: tiene_modulo(user, m) for m in MODULES}
