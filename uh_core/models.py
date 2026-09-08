from django.db import models


class Domicilio(models.Model):
    calle = models.CharField(max_length=255, blank=True, default="")
    numero_exterior = models.CharField(max_length=50, blank=True, default="")
    numero_interior = models.CharField(max_length=50, blank=True, default="")
    colonia = models.CharField(max_length=255, blank=True, default="")
    codigo_postal = models.CharField(max_length=20, blank=True, default="")
    municipio = models.CharField(max_length=255, blank=True, default="")
    estado = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "domicilios"

    def __str__(self) -> str:
        return f"{self.calle} {self.numero_exterior}".strip()


class DatosContacto(models.Model):
    telefono = models.CharField(max_length=50, blank=True, default="")
    celular = models.CharField(max_length=50, blank=True, default="")
    correo_electronico = models.EmailField(blank=True, default="")

    class Meta:
        db_table = "datos_contacto"

    def __str__(self) -> str:
        return self.correo_electronico or self.telefono or str(self.pk)


class Plantel(models.Model):
    clave_plantel = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255)
    rgp = models.CharField(max_length=100, blank=True, default="")
    registro_sep = models.CharField(max_length=100, blank=True, default="")
    pagina_web = models.URLField(blank=True, default="")
    domicilio = models.ForeignKey(Domicilio, on_delete=models.PROTECT, related_name="planteles")
    contacto = models.ForeignKey(DatosContacto, on_delete=models.PROTECT, related_name="planteles")

    class Meta:
        db_table = "planteles"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.clave_plantel})"


class Carrera(models.Model):
    plantel = models.ForeignKey(Plantel, on_delete=models.PROTECT, related_name="carreras")
    clave = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=255)
    regimen = models.CharField(max_length=30, blank=True, default="")
    tipo_periodo = models.ForeignKey("uh_academico.TipoPeriodo", on_delete=models.PROTECT, related_name="carreras", null=True, blank=True)
    total_ciclos = models.IntegerField(null=True, blank=True)
    acuerdo_sep = models.CharField(max_length=255, blank=True, default="")
    fecha_acuerdo_sep = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "carreras"

    def __str__(self) -> str:
        return self.nombre


class EstatusAcademico(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, default="")

    class Meta:
        db_table = "estatus_academico"

    def __str__(self) -> str:
        return self.nombre


class Autoridad(models.Model):
    titulo = models.CharField(max_length=20, blank=True, default="")
    nombres = models.CharField(max_length=255)
    apellidos = models.CharField(max_length=255)
    cargo = models.CharField(max_length=255)
    curp = models.CharField(max_length=18, blank=True, default="")
    firma_digital = models.FileField(upload_to="firmas/", blank=True, null=True)
    contacto = models.ForeignKey(DatosContacto, on_delete=models.PROTECT, related_name="autoridades", null=True, blank=True)

    class Meta:
        db_table = "autoridades"

    def __str__(self) -> str:
        nombre = f"{self.titulo} {self.nombres} {self.apellidos}".strip()
        return f"{nombre} - {self.cargo}".strip()


class PlantelAutoridad(models.Model):
    plantel = models.ForeignKey(Plantel, on_delete=models.CASCADE, related_name="plantel_autoridades")
    autoridad = models.ForeignKey(Autoridad, on_delete=models.CASCADE, related_name="plantel_autoridades")

    class Meta:
        db_table = "plantel_autoridades"
        unique_together = (("plantel", "autoridad"),)

    def __str__(self) -> str:
        return f"{self.plantel_id}-{self.autoridad_id}"


class ConfiguracionInstitucional(models.Model):
    nombre_institucion = models.CharField(max_length=255, default="Colegio Universitario Hispana")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuracion_institucional"
        verbose_name = "Configuración institucional"
        verbose_name_plural = "Configuraciones institucionales"

    def __str__(self) -> str:
        return self.nombre_institucion


# Create your models here.
