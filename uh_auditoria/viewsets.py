from __future__ import annotations

from datetime import datetime

from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from uh_auditoria.models import AuditoriaSistema
from uh_auditoria.serializers import AuditoriaSistemaSerializer
from uh_usuarios.access import es_admin
from uh_usuarios.permissions import permiso_modulo


class AuditoriaSistemaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditoriaSistemaSerializer

    def get_permissions(self):
        if es_admin(self.request.user):
            return [IsAuthenticated()]
        return [IsAuthenticated(), permiso_modulo("auditoria")()]

    def get_queryset(self):
        qs = AuditoriaSistema.objects.all().select_related("usuario").order_by("-fecha_hora", "-id")

        accion = (self.request.query_params.get("accion") or "").strip()
        modelo = (self.request.query_params.get("modelo_afectado") or "").strip()
        usuario = (self.request.query_params.get("usuario") or "").strip()
        desde = (self.request.query_params.get("desde") or "").strip()
        hasta = (self.request.query_params.get("hasta") or "").strip()

        if accion:
            qs = qs.filter(accion__icontains=accion)
        if modelo:
            qs = qs.filter(modelo_afectado__icontains=modelo)
        if usuario:
            if usuario.isdigit():
                qs = qs.filter(usuario_id=int(usuario))
            else:
                qs = qs.filter(usuario__username__icontains=usuario)

        def _parse(s: str) -> datetime | None:
            dt = parse_datetime(s)
            return dt

        if desde:
            dt = _parse(desde)
            if dt:
                qs = qs.filter(fecha_hora__gte=dt)
        if hasta:
            dt = _parse(hasta)
            if dt:
                qs = qs.filter(fecha_hora__lte=dt)

        return qs
