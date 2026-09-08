from django.db import migrations


def seed_tipos_documento(apps, schema_editor):
    TipoDocumento = apps.get_model("uh_documentos", "TipoDocumento")
    CategoriaDocumento = apps.get_model("uh_documentos", "CategoriaDocumento")

    categoria_constancias, _ = CategoriaDocumento.objects.get_or_create(
        nombre="Constancias"
    )

    TipoDocumento.objects.get_or_create(
        nombre="Constancia de Egreso",
        defaults={
            "descripcion": "Constancia para alumnos con estatus egresado o titulado.",
            "categoria": "CONSTANCIAS",
            "plantilla": "pdf/constancias/egreso.html",
            "aplica_a": "egresado,titulado",
            "reglas_validacion": {
                "estatus_permitidos": ["egresado", "titulado"]
            },
        },
    )

    TipoDocumento.objects.get_or_create(
        nombre="Constancia de Finalizacion con Titulacion en Proceso",
        defaults={
            "descripcion": "Constancia para alumnos con estatus egresado o titulado cuyo proceso de título está en trámite ante la SEP.",
            "categoria": "CONSTANCIAS",
            "plantilla": "pdf/constancias/egreso.html",
            "aplica_a": "egresado,titulado",
            "reglas_validacion": {
                "estatus_permitidos": ["egresado", "titulado"]
            },
        },
    )

    tipo, _ = TipoDocumento.objects.get_or_create(
        nombre="Constancia de Estudios",
        defaults={
            "descripcion": "Constancia para alumnos activos/regulares/inscritos.",
            "categoria": "CONSTANCIAS",
            "plantilla": "pdf/constancias/estudio.html",
            "aplica_a": "activo,regular,inscrito",
            "reglas_validacion": {
                "estatus_permitidos": [
                    "activo",
                    "regular",
                    "alumno regular",
                    "inscrito",
                ]
            },
        },
    )
    if categoria_constancias:
        tipo.categorias.add(categoria_constancias)


class Migration(migrations.Migration):
    dependencies = [
        ("uh_documentos", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tipos_documento, migrations.RunPython.noop),
    ]
