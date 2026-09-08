from django.core.exceptions import ValidationError
from django.db import models

from num2words import num2words

from uh_core.models import Carrera, DatosContacto, Domicilio, EstatusAcademico


class Alumno(models.Model):
    matricula = models.CharField(max_length=50, unique=True)
    foto = models.ImageField(upload_to="alumnos", blank=True, null=True)
    nombres = models.CharField(max_length=255)
    primer_apellido = models.CharField(max_length=255)
    segundo_apellido = models.CharField(max_length=255, blank=True, default="")
    curp = models.CharField(max_length=18, db_index=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=1, blank=True, default="")
    domicilio = models.ForeignKey(Domicilio, on_delete=models.PROTECT, related_name="alumnos")
    contacto = models.ForeignKey(DatosContacto, on_delete=models.PROTECT, related_name="alumnos")

    class Meta:
        db_table = "alumnos"

    def __str__(self) -> str:
        return f"{self.matricula} - {self.nombres} {self.primer_apellido}".strip()


class TrayectoriaAcademica(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="trayectorias")
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT, related_name="trayectorias")
    estatus_academico = models.ForeignKey(EstatusAcademico, on_delete=models.PROTECT, related_name="trayectorias")
    promedio_general = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    creditos_acumulados = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    nivel_actual = models.PositiveSmallIntegerField(null=True, blank=True)
    es_actual = models.BooleanField(default=True)
    titulacion_en_proceso = models.BooleanField(default=False)

    class Meta:
        db_table = "trayectoria_academica"

    def __str__(self) -> str:
        return f"{self.alumno_id}-{self.carrera_id}"

    def clean(self):
        if self.es_actual:
            qs = TrayectoriaAcademica.objects.filter(alumno=self.alumno, es_actual=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"es_actual": "Ya existe una trayectoria académica marcada como actual para este alumno."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PlanEstudio(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT, related_name="planes_estudio")
    clave_plan = models.CharField(max_length=50)
    version = models.IntegerField(default=1)
    creditos_totales = models.IntegerField(null=True, blank=True)
    vigencia_inicio = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "planes_estudio"
        unique_together = (("carrera", "clave_plan", "version"),)

    def __str__(self) -> str:
        return self.clave_plan


class Materia(models.Model):
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.PROTECT, related_name="materias")
    ciclo_numero = models.IntegerField()
    clave_materia = models.CharField(max_length=50)
    nombre_materia = models.CharField(max_length=255)
    creditos = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "catalogo_materias"
        unique_together = (("plan_estudio", "clave_materia"),)

    def __str__(self) -> str:
        return f"{self.clave_materia} - {self.nombre_materia}".strip()


class TipoPeriodo(models.Model):
    class Tipo(models.TextChoices):
        SEMESTRAL = "SEMESTRAL", "Semestral"
        CUATRIMESTRAL = "CUATRIMESTRAL", "Cuatrimestral"

    nombre = models.CharField(max_length=30, unique=True, choices=Tipo.choices)
    duracion_meses = models.PositiveSmallIntegerField()
    ciclos_por_anio = models.PositiveSmallIntegerField(default=2)

    class Meta:
        db_table = "tipos_periodo"
        verbose_name = "Tipo de periodo"
        verbose_name_plural = "Tipos de periodo"

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        if self.pk and TipoPeriodo.objects.filter(pk=self.pk).exists():
            original = TipoPeriodo.objects.get(pk=self.pk)
            if original.nombre != self.nombre or original.duracion_meses != self.duracion_meses or original.ciclos_por_anio != self.ciclos_por_anio:
                raise ValueError("Los tipos de periodo no pueden modificarse.")
        super().save(*args, **kwargs)


class PeriodoAcademico(models.Model):
    ciclo_escolar = models.ForeignKey("CicloEscolar", on_delete=models.PROTECT, related_name="periodos", null=True, blank=True)
    tipo_periodo = models.ForeignKey(TipoPeriodo, on_delete=models.PROTECT, related_name="periodos", null=True, blank=True)
    clave = models.CharField(max_length=20, blank=True, default="")
    numero = models.PositiveSmallIntegerField(null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "periodos_academicos"
        unique_together = (("ciclo_escolar", "tipo_periodo", "numero"),)

    def __str__(self) -> str:
        return self.clave


class CicloEscolar(models.Model):
    anio_inicio = models.IntegerField(null=True, blank=True)
    anio_fin = models.IntegerField(null=True, blank=True)
    clave = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "ciclos_escolares"
        unique_together = (("anio_inicio", "anio_fin"),)

    def clean(self):
        if self.anio_inicio is not None and self.anio_fin is not None:
            qs = CicloEscolar.objects.filter(anio_inicio=self.anio_inicio, anio_fin=self.anio_fin)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"anio_inicio": "Ya existe un ciclo escolar con esos años.", "anio_fin": "Ya existe un ciclo escolar con esos años."})

    def save(self, *args, **kwargs):
        if not self.clave:
            self.clave = f"{self.anio_inicio}-{self.anio_fin}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.clave


class InscripcionPeriodo(models.Model):
    ESTATUS_INSCRITO = "INSCRITO"
    ESTATUS_CURSANDO = "CURSANDO"
    ESTATUS_BAJA = "BAJA"
    ESTATUS_CONCLUIDO = "CONCLUIDO"
    ESTATUS_SUSPENDIDO = "SUSPENDIDO"

    ESTATUS_CHOICES = (
        (ESTATUS_INSCRITO, "Inscrito"),
        (ESTATUS_CURSANDO, "Cursando"),
        (ESTATUS_BAJA, "Baja"),
        (ESTATUS_CONCLUIDO, "Concluido"),
        (ESTATUS_SUSPENDIDO, "Suspendido"),
    )

    trayectoria_academica = models.ForeignKey(
        TrayectoriaAcademica,
        on_delete=models.CASCADE,
        related_name="inscripciones_periodo",
    )
    periodo_academico = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="inscripciones_periodo",
    )
    promedio_periodo = models.FloatField(null=True, blank=True)
    estatus = models.CharField(max_length=30, blank=True, default=ESTATUS_CURSANDO, choices=ESTATUS_CHOICES)
    es_actual = models.BooleanField(default=False)

    class Meta:
        db_table = "inscripciones_periodo"
        unique_together = (("trayectoria_academica", "periodo_academico"),)

    def __str__(self) -> str:
        return f"{self.trayectoria_academica_id}-{self.periodo_academico_id}"

    def clean(self):
        if self.es_actual:
            qs = InscripcionPeriodo.objects.filter(trayectoria_academica=self.trayectoria_academica, es_actual=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"es_actual": "Ya existe una inscripción de periodo marcada como actual para esta trayectoria."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CalificacionDetalle(models.Model):
    inscripcion_periodo = models.ForeignKey(
        InscripcionPeriodo,
        on_delete=models.CASCADE,
        related_name="calificaciones",
    )
    catalogo_materia = models.ForeignKey(
        Materia,
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )
    calificacion_ordinaria = models.FloatField(null=True, blank=True)
    extraordinario_1 = models.FloatField(null=True, blank=True)
    extraordinario_2 = models.FloatField(null=True, blank=True)
    calificacion_final = models.FloatField(null=True, blank=True)
    calificacion_letra = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "calificaciones_detalle"
        unique_together = (("inscripcion_periodo", "catalogo_materia"),)

    def save(self, *args, **kwargs):
        if self.calificacion_final is not None:
            texto = str(self.calificacion_final)
            if "." in texto:
                entero, decimal = texto.split(".")
                decimal = decimal.rstrip("0")
                if decimal:
                    self.calificacion_letra = (
                        num2words(int(entero), lang="es").upper()
                        + " PUNTO "
                        + " ".join(num2words(int(d), lang="es").upper() for d in decimal)
                    )
                else:
                    self.calificacion_letra = num2words(int(entero), lang="es").upper() + " PUNTO CERO"
            else:
                self.calificacion_letra = num2words(int(self.calificacion_final), lang="es").upper()
        else:
            self.calificacion_letra = ""
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.inscripcion_periodo_id}-{self.catalogo_materia_id}"
