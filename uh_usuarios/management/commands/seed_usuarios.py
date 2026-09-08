import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from uh_core.models import Autoridad
from uh_usuarios.models import PerfilUsuario, Rol


def slug_username(autoridad: Autoridad, usados: set) -> str:
    base = ""
    if autoridad.nombres:
        base += autoridad.nombres[0]
    if autoridad.apellidos:
        base += autoridad.apellidos.split()[0] if autoridad.apellidos.split() else ""
    base = base.lower().replace(" ", "")
    if not base:
        base = "autoridad"
    candidato = base
    n = 1
    while candidato in usados:
        n += 1
        candidato = f"{base}{n}"
    usados.add(candidato)
    return candidato


class Command(BaseCommand):
    help = "Genera roles a partir de los cargos de las autoridades y crea usuarios de prueba ligados a cada autoridad."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Hispana2025*",
            help="Contraseña inicial para los usuarios generados (default: Hispana2025*).",
        )
        parser.add_argument(
            "--solo-figueroa",
            action="store_true",
            help="Solo asegura el usuario de prueba Lic. Carlos Figueroa.",
        )
        parser.add_argument(
            "--reset-defaults",
            action="store_true",
            help="Normaliza los permisos por defecto de los roles no-admin (dashboard/auditoria/catalogos en False).",
        )

    def handle(self, *args, **options):
        password = options["password"]
        solo_figueroa = options["solo_figueroa"]
        User = get_user_model()

        if options["reset_defaults"]:
            actualizados = 0
            for rol in Rol.objects.filter(es_admin=False):
                if rol.puede_dashboard or rol.puede_auditoria or rol.puede_catalogos:
                    rol.puede_dashboard = False
                    rol.puede_auditoria = False
                    rol.puede_catalogos = False
                    rol.save()
                    actualizados += 1
            self.stdout.write(
                self.style.SUCCESS(f"Roles no-admin normalizados (dashboard/auditoria/catalogos=False): {actualizados}")
            )
            return

        # 1) Roles a partir de los cargos de autoridades
        cargos = (
            Autoridad.objects.exclude(cargo__isnull=True)
            .exclude(cargo="")
            .values_list("cargo", flat=True)
            .distinct()
        )
        roles_por_cargo: dict[str, Rol] = {}
        for cargo in cargos:
            rol, creado = Rol.objects.get_or_create(
                nombre=cargo,
                defaults={
                    "puede_dashboard": False,
                    "puede_auditoria": False,
                    "puede_catalogos": False,
                },
            )
            if creado:
                self.stdout.write(self.style.SUCCESS(f"  Rol creado: {cargo}"))
            else:
                self.stdout.write(f"  Rol existente: {cargo}")
            roles_por_cargo[cargo] = rol

        self.stdout.write(self.style.MIGRATE_HEADING("Roles disponibles:"))
        for cargo, rol in roles_por_cargo.items():
            self.stdout.write(f"  - {cargo}")

        # 2) Usuarios ligados a autoridades
        autoridades = Autoridad.objects.all().order_by("id")
        if solo_figueroa:
            autoridades = autoridades.filter(
                nombres__icontains="carlos", apellidos__icontains="figueroa"
            )

        usados: set[str] = set(
            User.objects.values_list("username", flat=True)
        )
        creados = []
        for auth in autoridades:
            if PerfilUsuario.objects.filter(autoridad=auth).exists():
                self.stdout.write(f"  Ya existe usuario para {auth} — omitido.")
                continue
            username = slug_username(auth, usados)
            nombre_completo = f"{auth.nombres} {auth.apellidos}".strip()
            user = User.objects.create_user(
                username=username,
                email=f"{username}@uhispanacf.mx",
                password=password,
                first_name=auth.nombres,
                last_name=auth.apellidos,
            )
            perfil = PerfilUsuario.objects.create(
                user=user,
                autoridad=auth,
                rol=roles_por_cargo.get(auth.cargo),
            )
            creados.append((username, nombre_completo, auth.cargo, perfil.rol.nombre if perfil.rol else "—"))
            self.stdout.write(self.style.SUCCESS(f"  Usuario creado: {username} -> {nombre_completo}"))

        if creados:
            self.stdout.write(self.style.MIGRATE_HEADING("Credenciales generadas (contraseña: %s):" % password))
            for username, nombre, cargo, rol in creados:
                self.stdout.write(f"  {username:20s} | {nombre:30s} | rol: {rol}")
        else:
            self.stdout.write("No se crearon usuarios nuevos.")
