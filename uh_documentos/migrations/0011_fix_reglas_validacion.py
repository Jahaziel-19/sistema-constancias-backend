from django.db import migrations


def fix_reglas_validacion(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")

    TipoDocumento.objects.filter(nombre="Constancia de Finalizacion con Titulacion en Proceso").update(
        reglas_validacion={
            "requiere_estatus": ["Egresado", "Titulado"],
            "requiere_titulacion_en_proceso": True,
        }
    )

    TipoDocumento.objects.filter(nombre="Constancia de Finalizacion sin Titulacion Iniciada").update(
        reglas_validacion={
            "requiere_estatus": ["Egresado", "Titulado"],
            "requiere_titulacion_en_proceso": False,
        }
    )


def rollback(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("uh_documentos", "0010_alter_tipodocumento_categoria"),
    ]

    operations = [
        migrations.RunPython(fix_reglas_validacion, rollback),
    ]
