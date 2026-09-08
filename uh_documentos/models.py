from django.db import models

from uh_academico.models import Alumno
from uh_core.models import Autoridad, DatosContacto, Plantel


class CategoriaDocumento(models.Model):
    nombre = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "categorias_documento"

    def __str__(self) -> str:
        return self.nombre


class TipoDocumento(models.Model):
    CONSTANCIAS = "CONSTANCIAS"
    KARDEX = "KARDEX"
    #DIPLOMAS = "DIPLOMAS"
    #RECONOCIMIENTOS = "RECONOCIMIENTOS"
    TITULO = "TITULO"
    DIPLOMAS_RECONOCIMIENTOS = "DIPLOMAS_RECONOCIMIENTOS"

    CATEGORIA_CHOICES = (
        (CONSTANCIAS, "Constancias"),
        (KARDEX, "Kardex"),
        #(DIPLOMAS, "Diplomas"),
        #(RECONOCIMIENTOS, "Reconocimientos"),
        (TITULO, "Títulos"),
        (DIPLOMAS_RECONOCIMIENTOS, "Diplomas y Reconocimientos"),
    )

    nombre = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True, default="")
    aplica_a = models.CharField(max_length=50, blank=True, default="")
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, default=CONSTANCIAS)
    categorias = models.ManyToManyField(CategoriaDocumento, blank=True)
    plantilla = models.CharField(max_length=255, blank=True, default="pdf/constancias/estudio.html")
    reglas_validacion = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "tipos_documento"

    def __str__(self):
        return self.nombre


class Externo(models.Model):
    nombres = models.CharField(max_length=255)
    primer_apellido = models.CharField(max_length=255, blank=True, default="")
    segundo_apellido = models.CharField(max_length=255, blank=True, default="")
    contacto = models.ForeignKey(DatosContacto, on_delete=models.PROTECT, related_name="externos", null=True, blank=True)

    class Meta:
        db_table = "externos"

    def __str__(self) -> str:
        return f"{self.nombres} {self.primer_apellido} {self.segundo_apellido}".strip()


class DestinatarioPolimorfico(models.Model):
    entidad_tipo = models.CharField(max_length=20)
    entidad_id = models.IntegerField()

    class Meta:
        db_table = "destinatarios_polimorficos"

    def __str__(self) -> str:
        return f"{self.entidad_tipo}:{self.entidad_id}"


class DocumentoEmitido(models.Model):
    folio = models.CharField(max_length=50, unique=True)
    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT, related_name="documentos")
    plantel = models.ForeignKey(Plantel, on_delete=models.PROTECT, related_name="documentos")
    autoridad = models.ForeignKey(Autoridad, on_delete=models.PROTECT, related_name="documentos", null=True, blank=True)
    destinatario = models.ForeignKey(
        DestinatarioPolimorfico,
        on_delete=models.PROTECT,
        related_name="documentos",
        null=True,
        blank=True,
    )
    alumno = models.ForeignKey(Alumno, on_delete=models.PROTECT, related_name="documentos", null=True, blank=True)
    externo = models.ForeignKey(Externo, on_delete=models.PROTECT, related_name="documentos", null=True, blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    hash_documento = models.CharField(max_length=128, db_index=True)
    snapshot_datos_receptor = models.JSONField(default=dict, blank=True)
    snapshot_academico = models.JSONField(default=dict, blank=True)
    archivo = models.FileField(upload_to="documentos/", null=True, blank=True)
    html_renderizado = models.TextField(blank=True, default="")
    es_valido = models.BooleanField(default=True)

    class Meta:
        db_table = "documentos_emitidos"

    def __str__(self) -> str:
        return self.folio
