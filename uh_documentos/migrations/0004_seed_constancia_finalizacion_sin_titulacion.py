from django.db import migrations


def seed_constancia_finalizacion_sin_titulacion(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")
    CategoriaDocumento = apps.get_model("uh_documentos", "CategoriaDocumento")

    categoria_constancias, _ = CategoriaDocumento.objects.get_or_create(
        nombre="Constancias"
    )

    TipoDocumento.objects.get_or_create(
        nombre="Finalizacion de estudios sin proceso de titulacion",
        defaults={
            "descripcion": "Constancia para alumnos egresados o titulados que no cuentan con proceso de titulación.",
            "categoria": "CONSTANCIAS",
            "plantilla": "pdf/constancias/egreso.html",
            "aplica_a": "egresado,titulado",
            "reglas_validacion": {
                "estatus_permitidos": ["egresado", "titulado"]
            },
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("uh_documentos", "0003_seed_constancia_finalizacion_titulacion"),
    ]

    operations = [
        migrations.RunPython(seed_constancia_finalizacion_sin_titulacion, migrations.RunPython.noop),
    ]
