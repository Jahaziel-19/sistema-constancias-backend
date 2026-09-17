from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = "Carga fixtures JSON omitiendo registros existentes"

    def add_arguments(self, parser):
        parser.add_argument("fixture", help="Ruta al archivo fixture JSON")

    def handle(self, *args, **options):
        fixture_path = options["fixture"]
        self.stdout.write(self.style.NOTICE(f"Cargando: {fixture_path}"))

        loaded = 0
        skipped = 0
        errors = 0

        with open(fixture_path, "r", encoding="utf-8") as f:
            for obj in serializers.deserialize("json", f, ignorenonexistent=True):
                model_label = obj.object._meta.label_lower

                try:
                    with transaction.atomic():
                        obj.save()
                        loaded += 1
                except IntegrityError as e:
                    skipped += 1
                    msg = str(e).lower()
                    if "duplicate" in msg or "unique" in msg or "already" in msg or "exist" in msg:
                        self.stdout.write(self.style.WARNING(f"Saltado (existe): {model_label}"))
                    else:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f"Integridad: {model_label}: {e}"))
                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"Error: {model_label}: {e}"))

                if loaded % 100 == 0:
                    self.stdout.write(self.style.NOTICE(f"Progreso: cargados={loaded}, saltados={skipped}"))

        self.stdout.write(self.style.SUCCESS(
            f"Complete: cargados={loaded}, saltados={skipped}, errores={errors}"
        ))
