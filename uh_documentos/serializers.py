from rest_framework import serializers

from uh_documentos.models import CategoriaDocumento, DocumentoEmitido, Externo, TipoDocumento


class CategoriaDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaDocumento
        fields = "__all__"


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = "__all__"


class ExternoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Externo
        fields = "__all__"


class DocumentoEmitidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoEmitido
        fields = "__all__"
        read_only_fields = ["folio", "hash_documento", "fecha_emision", "snapshot_datos_receptor", "snapshot_academico"]


class DocumentoEmitidoCreateSerializer(serializers.Serializer):
    tipo_documento_id = serializers.IntegerField()
    plantel_id = serializers.IntegerField()
    autoridad_id = serializers.IntegerField(required=False, allow_null=True)
    alumno_id = serializers.IntegerField(required=False, allow_null=True)
    externo_nombres = serializers.CharField(required=False, allow_blank=True)
    externo_apellidos = serializers.CharField(required=False, allow_blank=True)
    externo_correo = serializers.EmailField(required=False, allow_blank=True)
    externo_telefono = serializers.CharField(required=False, allow_blank=True)
    aprobado_directiva = serializers.BooleanField(required=False, default=True)
    archivo = serializers.FileField(required=False, allow_null=True)
    descripcion_nombramiento = serializers.CharField(required=False, allow_blank=True)
    institucion_otorgante = serializers.CharField(required=False, allow_blank=True)
    folio_sep = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        alumno_id = attrs.get("alumno_id")
        externo_nombres = (attrs.get("externo_nombres") or "").strip()
        if bool(alumno_id) == bool(externo_nombres):
            raise serializers.ValidationError("Debes enviar alumno_id o externo_nombres (solo uno).")
        if externo_nombres and not (attrs.get("externo_apellidos") or "").strip():
            attrs["externo_apellidos"] = ""
        return attrs


class DocumentoPublicoSerializer(serializers.ModelSerializer):
    tipo_documento = serializers.CharField(source="tipo_documento.nombre", read_only=True)
    calificaciones = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoEmitido
        fields = [
            "folio",
            "tipo_documento",
            "fecha_emision",
            "es_valido",
            "snapshot_datos_receptor",
            "snapshot_academico",
            "calificaciones",
        ]

    def get_calificaciones(self, obj):
        return self.context.get("calificaciones") or []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        receptor = data.get("snapshot_datos_receptor") or {}
        academico = data.get("snapshot_academico") or {}
        if isinstance(receptor, dict):
            data["snapshot_datos_receptor"] = {k: v for k, v in receptor.items() if not k.startswith("id_")}
        if isinstance(academico, dict):
            data["snapshot_academico"] = {k: v for k, v in academico.items() if not k.startswith("id_")}
        return data
