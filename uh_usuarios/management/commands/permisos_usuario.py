from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from uh_usuarios.access import MODULES
from uh_usuarios.models import PerfilUsuario


class Command(BaseCommand):
    help = "Gestiona los permisos personalizados de un usuario (overrides al rol)."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Nombre de usuario a gestionar.")
        parser.add_argument(
            "--grant",
            nargs="+",
            metavar="MODULO",
            help="Módulos a conceder explícitamente (dashboard, alumnos, ...).",
        )
        parser.add_argument(
            "--revoke",
            nargs="+",
            metavar="MODULO",
            help="Módulos a denegar explícitamente.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Elimina todas las personalizaciones y vuelve a los defaults del rol.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"Usuario '{options['username']}' no existe.")

        perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
        personalizados = dict(perfil.permisos_personalizados or {})

        invalidos = []
        for m in (options.get("grant") or []) + (options.get("revoke") or []):
            if m not in MODULES:
                invalidos.append(m)
        if invalidos:
            raise CommandError(
                "Módulos inválidos: %s. Válidos: %s" % (", ".join(invalidos), ", ".join(MODULES))
            )

        cambios = False
        if options["clear"]:
            personalizados = {}
            cambios = True
        for m in options.get("grant") or []:
            personalizados[m] = True
            cambios = True
        for m in options.get("revoke") or []:
            personalizados[m] = False
            cambios = True

        if cambios:
            perfil.permisos_personalizados = personalizados
            perfil.save()
            self.stdout.write(self.style.SUCCESS("Permisos personalizados actualizados."))

        self.stdout.write(self.style.MIGRATE_HEADING(f"Usuario: {user.get_username()}"))
        self.stdout.write(f"  Rol: {perfil.rol.nombre if perfil.rol else '—'}")
        self.stdout.write("  Permisos efectivos:")
        for m in MODULES:
            fuente = "personalizado" if m in personalizados else ("rol" if perfil.rol else "default")
            valor = personalizados.get(m) if m in personalizados else None
            if valor is None:
                if perfil.rol:
                    valor = getattr(perfil.rol, f"puede_{m}", False)
                else:
                    valor = m in ("emision", "alumnos", "calificaciones", "registros", "ciclos")
            self.stdout.write(f"    - {m:14s}: {'SÍ' if valor else 'NO'}  ({fuente})")
