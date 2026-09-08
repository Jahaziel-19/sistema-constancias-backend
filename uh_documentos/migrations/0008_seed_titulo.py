from django.db import migrations


def seed_titulo(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")
    TipoDocumento.objects.get_or_create(
        nombre="Título Profesional",
        defaults={
            "descripcion": (
                "Título digital oficial expedido por la Universidad a alumnos que "
                "han obtenido el grado de Titulado. Requiere folio SEP y sólo se "
                "puede emitir una vez por persona."
            ),
            "aplica_a": "alumnos",
            "categoria": TipoDocumento.TITULO if hasattr(TipoDocumento, "TITULO") else "TITULO",
            "plantilla": "",
            "reglas_validacion": {
                "requiere_aprobacion_directiva": True,
                "requiere_autoridad": True,
                "solo_estatus_titulado": True,
                "unico_por_alumno": True,
            },
        },
    )


def unseed(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")
    TipoDocumento.objects.filter(nombre="Título Profesional").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("uh_documentos", "0007_seed_diploma_reconocimiento"),
    ]

    operations = [
        migrations.RunPython(seed_titulo, reverse_code=unseed),
    ]
