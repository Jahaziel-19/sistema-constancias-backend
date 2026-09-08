from rest_framework import serializers

from uh_auditoria.models import AuditoriaSistema


class AuditoriaSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditoriaSistema
        fields = "__all__"
