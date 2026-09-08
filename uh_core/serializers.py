from rest_framework import serializers

from uh_core.models import Autoridad, Carrera, ConfiguracionInstitucional, DatosContacto, Domicilio, EstatusAcademico, Plantel


class DomicilioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domicilio
        fields = "__all__"


class DatosContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatosContacto
        fields = "__all__"


class PlantelSerializer(serializers.ModelSerializer):
    domicilio = DomicilioSerializer(read_only=True)
    contacto = DatosContactoSerializer(read_only=True)
    domicilio_id = serializers.PrimaryKeyRelatedField(source="domicilio", queryset=Domicilio.objects.all(), write_only=True)
    contacto_id = serializers.PrimaryKeyRelatedField(source="contacto", queryset=DatosContacto.objects.all(), write_only=True)

    class Meta:
        model = Plantel
        fields = [
            "id",
            "clave_plantel",
            "nombre",
            "rgp",
            "registro_sep",
            "pagina_web",
            "domicilio",
            "contacto",
            "domicilio_id",
            "contacto_id",
        ]


class CarreraSerializer(serializers.ModelSerializer):
    plantel_id = serializers.IntegerField(required=False)
    tipo_periodo_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Carrera
        fields = [
            "id",
            "plantel",
            "plantel_id",
            "tipo_periodo",
            "tipo_periodo_id",
            "clave",
            "nombre",
            "regimen",
            "total_ciclos",
            "acuerdo_sep",
            "fecha_acuerdo_sep",
        ]


class EstatusAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstatusAcademico
        fields = "__all__"


class AutoridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autoridad
        fields = "__all__"


class ConfiguracionInstitucionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionInstitucional
        fields = "__all__"
