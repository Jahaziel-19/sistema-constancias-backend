from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = "Carga fixtures JSON omitiendo registros existentes (multi-paso para FK)"

    def add_arguments(self, parser):
        parser.add_argument("fixture", help="Ruta al archivo fixture JSON")
        parser.add_argument(
            "--max-passes",
            type=int,
            default=10,
            help="Número máximo de pasadas para resolver dependencias (default: 10)",
        )

    def handle(self, *args, **options):
        fixture_path = options["fixture"]
        max_passes = options["max_passes"]
        self.stdout.write(self.style.NOTICE(f"Cargando: {fixture_path}"))

        with open(fixture_path, "r", encoding="utf-8") as f:
            all_objects = list(serializers.deserialize("json", f, ignorenonexistent=True))

        total = len(all_objects)
        self.stdout.write(self.style.NOTICE(f"Total de registros en fixture: {total}"))

        pending = all_objects
        loaded_total = 0
        skipped_total = 0
        errors_total = 0
        pass_num = 0

        while pending and pass_num < max_passes:
            pass_num += 1
            loaded = 0
            skipped = 0
            errors = 0
            deferred = []

            self.stdout.write(self.style.NOTICE(f"--- Pasada {pass_num} ({len(pending)} pendientes) ---"))

            for obj in pending:
                model_label = obj.object._meta.label_lower

                try:
                    with transaction.atomic():
                        obj.save()
                        loaded += 1
                except IntegrityError as e:
                    skipped += 1
                    msg = str(e).lower()
                    if "duplicate" in msg or "unique" in msg or "already" in msg or "exist" in msg:
                        deferred.append(obj)
                    else:
                        errors += 1
                        errors_total += 1
                        self.stdout.write(self.style.ERROR(f"Integridad: {model_label}: {e}"))
                except Exception as e:
                    errors += 1
                    errors_total += 1
                    self.stdout.write(self.style.ERROR(f"Error: {model_label}: {e}"))

            loaded_total += loaded
            skipped_total += skipped

            if loaded > 0:
                self.stdout.write(self.style.SUCCESS(f"Pasada {pass_num}: cargados={loaded}, saltados={skipped}"))

            if not deferred:
                break

            pending = deferred

        if pending:
            self.stdout.write(self.style.WARNING(
                f"{len(pending)} registros no pudieron cargarse (dependencias no resueltas)"
            ))
            for obj in pending[:20]:
                self.stdout.write(self.style.WARNING(f"  - {obj.object._meta.label_lower} pk={getattr(obj.object, 'pk', '?')}"))

        self.stdout.write(self.style.SUCCESS(
            f"Complete: cargados={loaded_total}, saltados={skipped_total}, errores={errors_total}, pasadas={pass_num}"
        ))
