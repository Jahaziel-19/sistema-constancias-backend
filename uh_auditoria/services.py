from __future__ import annotations

from typing import Any

from uh_auditoria.models import AuditoriaSistema


def registrar_auditoria(
    *,
    request: Any,
    accion: str,
    modelo_afectado: str = "",
    registro_id: int | None = None,
    detalles_cambio: dict[str, Any] | None = None,
) -> None:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False) is False:
        user = None
    ip = getattr(request, "META", {}).get("REMOTE_ADDR")
    AuditoriaSistema.objects.create(
        usuario=user,
        accion=accion,
        modelo_afectado=modelo_afectado,
        registro_id=registro_id,
        detalles_cambio=detalles_cambio or {},
        ip_origen=ip,
    )
