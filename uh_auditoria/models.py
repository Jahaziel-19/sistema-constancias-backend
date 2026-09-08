from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditoriaSistema(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    accion = models.CharField(max_length=100)
    modelo_afectado = models.CharField(max_length=100, blank=True, default="")
    registro_id = models.BigIntegerField(null=True, blank=True)
    detalles_cambio = models.JSONField(default=dict, blank=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "auditoria_sistema"

    def __str__(self) -> str:
        return f"{self.accion} {self.modelo_afectado} {self.registro_id or ''}".strip()
