from django.db import migrations


def seed_diploma_reconocimiento(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")

    TipoDocumento.objects.get_or_create(
        nombre="Diploma y Reconocimiento",
        defaults={
            "descripcion": "Formato base unificado para emitir diplomas y reconocimientos a alumnos o externos. Requiere descripción del nombramiento e institución otorgante.",
            "aplica_a": "ambos",
            "categoria": "DIPLOMAS_RECONOCIMIENTOS",
            "plantilla": "",
            "reglas_validacion": {
                "requiere_aprobacion_directiva": True,
            },
        },
    )


def rollback(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")
    TipoDocumento.objects.filter(nombre="Diploma y Reconocimiento").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("uh_documentos", "0006_alter_tipodocumento_categoria"),
    ]

    operations = [
        migrations.RunPython(seed_diploma_reconocimiento, rollback),
    ]
