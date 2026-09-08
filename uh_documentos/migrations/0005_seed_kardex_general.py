from django.db import migrations


def seed_kardex_general(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")
    CategoriaDocumento = apps.get_model("uh_documentos", "CategoriaDocumento")

    categoria_kardex, _ = CategoriaDocumento.objects.get_or_create(
        nombre="Kardex"
    )

    TipoDocumento.objects.get_or_create(
        nombre="Kardex General",
        defaults={
            "descripcion": "Kardex académico general del alumno con calificaciones por periodo.",
            "categoria": "KARDEX",
            "plantilla": "kardex.html",
            "aplica_a": "activo,regular,inscrito,egresado,titulado",
            "reglas_validacion": {},
        },
    )

    tipo, _ = TipoDocumento.objects.get_or_create(
        nombre="Kardex de alumno",
        defaults={
            "descripcion": "Kardex individual por alumno.",
            "categoria": "KARDEX",
            "plantilla": "kardex.html",
            "aplica_a": "activo,regular,inscrito,egresado,titulado",
            "reglas_validacion": {},
        },
    )
    if categoria_kardex:
        tipo.categorias.add(categoria_kardex)


class Migration(migrations.Migration):
    dependencies = [
        ("uh_documentos", "0004_seed_constancia_finalizacion_sin_titulacion"),
    ]

    operations = [
        migrations.RunPython(seed_kardex_general, migrations.RunPython.noop),
    ]
