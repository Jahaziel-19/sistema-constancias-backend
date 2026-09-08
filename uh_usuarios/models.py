from django.conf import settings
from django.db import models

from uh_core.models import Autoridad


class Rol(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True, default="")
    es_admin = models.BooleanField(
        default=False,
        help_text="Acceso total al sistema (equivalente a staff/admin).",
    )
    puede_dashboard = models.BooleanField(default=False)
    puede_auditoria = models.BooleanField(default=False)
    puede_catalogos = models.BooleanField(default=False)
    puede_emision = models.BooleanField(default=True)
    puede_alumnos = models.BooleanField(default=True)
    puede_calificaciones = models.BooleanField(default=True)
    puede_registros = models.BooleanField(default=True)
    puede_ciclos = models.BooleanField(default=True)

    class Meta:
        db_table = "roles"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre

    def acceso_modulo(self, modulo: str) -> bool:
        if self.es_admin:
            return True
        return bool(getattr(self, f"puede_{modulo}", False))


class PerfilUsuario(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    autoridad = models.ForeignKey(
        Autoridad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfiles",
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfiles",
    )
    permisos_personalizados = models.JSONField(
        default=dict,
        blank=True,
        help_text="Overrides por usuario. Cada clave es un módulo y el valor (bool) anula el default del rol.",
    )

    class Meta:
        db_table = "perfiles_usuario"

    def __str__(self) -> str:
        nombre = self.user.get_username() if self.user_id else "?"
        return f"Perfil de {nombre}"
