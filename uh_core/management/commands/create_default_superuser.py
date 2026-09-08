from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Crea un superusuario por defecto si no existe."

    def handle(self, *args, **options):
        username = "admin"
        email = "admin@hispana.edu.mx"
        password = "Admin123*"
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superusuario creado: {username} / {password}"))
        else:
            self.stdout.write(self.style.WARNING("El superusuario ya existe."))
