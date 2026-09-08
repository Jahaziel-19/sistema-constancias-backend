from rest_framework import serializers

from uh_academico.models import (
    Alumno,
    CalificacionDetalle,
    CicloEscolar,
    InscripcionPeriodo,
    Materia,
    PeriodoAcademico,
    PlanEstudio,
    TrayectoriaAcademica,
    TipoPeriodo,
)
from uh_core.models import DatosContacto, Domicilio
from uh_core.serializers import DatosContactoSerializer, DomicilioSerializer


class AlumnoSerializer(serializers.ModelSerializer):
    domicilio = DomicilioSerializer(read_only=True)
    contacto = DatosContactoSerializer(read_only=True)
    domicilio_id = serializers.PrimaryKeyRelatedField(source="domicilio", queryset=Domicilio.objects.all(), write_only=True)
    contacto_id = serializers.PrimaryKeyRelatedField(source="contacto", queryset=DatosContacto.objects.all(), write_only=True)
    nivel_actual = serializers.SerializerMethodField()

    class Meta:
        model = Alumno
        fields = [
            "id",
            "matricula",
            "foto",
            "nombres",
            "primer_apellido",
            "segundo_apellido",
            "curp",
            "fecha_nacimiento",
            "genero",
            "domicilio",
            "contacto",
            "domicilio_id",
            "contacto_id",
            "nivel_actual",
        ]

    def get_nivel_actual(self, obj):
        t = obj.trayectorias.filter(es_actual=True).first()
        return t.nivel_actual if t else ""


class TrayectoriaAcademicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrayectoriaAcademica
        fields = "__all__"

    def validate(self, data):
        if data.get("es_actual"):
            alumno = data.get("alumno") or (self.instance.alumno if self.instance else None)
            if alumno:
                qs = TrayectoriaAcademica.objects.filter(alumno=alumno, es_actual=True)
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError({"es_actual": "Ya existe una trayectoria académica marcada como actual para este alumno."})
        return data


class TipoPeriodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPeriodo
        fields = "__all__"


class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoAcademico
        fields = "__all__"

    def validate(self, data):
        ciclo = data.get("ciclo_escolar")
        tipo = data.get("tipo_periodo")
        numero = data.get("numero")
        if ciclo is not None and tipo is not None and numero is not None:
            qs = PeriodoAcademico.objects.filter(ciclo_escolar=ciclo, tipo_periodo=tipo, numero=numero)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"ciclo_escolar": "Ya existe un periodo académico con esa combinación de ciclo, tipo y número.", "tipo_periodo": "Ya existe un periodo académico con esa combinación de ciclo, tipo y número.", "numero": "Ya existe un periodo académico con esa combinación de ciclo, tipo y número."}
                )
        return data


class CicloEscolarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloEscolar
        fields = "__all__"

    def validate(self, data):
        anio_inicio = data.get("anio_inicio")
        anio_fin = data.get("anio_fin")
        if anio_inicio is not None and anio_fin is not None:
            qs = CicloEscolar.objects.filter(anio_inicio=anio_inicio, anio_fin=anio_fin)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"anio_inicio": "Ya existe un ciclo escolar con esos años.", "anio_fin": "Ya existe un ciclo escolar con esos años."}
                )
        return data


class InscripcionPeriodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InscripcionPeriodo
        fields = "__all__"

    def validate(self, data):
        if data.get("es_actual"):
            trayectoria = data.get("trayectoria_academica") or (self.instance.trayectoria_academica if self.instance else None)
            if trayectoria:
                qs = InscripcionPeriodo.objects.filter(trayectoria_academica=trayectoria, es_actual=True)
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError({"es_actual": "Ya existe una inscripción de periodo marcada como actual para esta trayectoria."})
        return data


class CalificacionDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalificacionDetalle
        fields = "__all__"


class PlanEstudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanEstudio
        fields = "__all__"


class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = "__all__"
