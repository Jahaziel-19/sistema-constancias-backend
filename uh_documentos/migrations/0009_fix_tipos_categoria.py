from django.db import migrations


def fix_tipos_categoria(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")

    updates = {
        "Diploma y Reconocimiento": "DIPLOMAS_RECONOCIMIENTOS",
        "Diploma en Optometria": "DIPLOMAS_RECONOCIMIENTOS",
        "Reconocimiento Honoris Causa": "DIPLOMAS_RECONOCIMIENTOS",
    }

    for nombre, categoria in updates.items():
        TipoDocumento.objects.filter(nombre=nombre).update(categoria=categoria)


def rollback(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("uh_documentos", "0008_seed_titulo"),
    ]

    operations = [
        migrations.RunPython(fix_tipos_categoria, rollback),
    ]
