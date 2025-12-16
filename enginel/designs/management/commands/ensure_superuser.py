"""
Management command to create a default superuser if none exists.
Usage: python manage.py ensure_superuser
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'),
            help='Superuser username (default: admin or DJANGO_SUPERUSER_USERNAME env var)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default=os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'),
            help='Superuser email (default: admin@example.com or DJANGO_SUPERUSER_EMAIL env var)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=os.getenv('DJANGO_SUPERUSER_PASSWORD'),
            help='Superuser password (default: DJANGO_SUPERUSER_PASSWORD env var)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists. Skipping creation.')
            )
            return

        if not password:
            self.stdout.write(
                self.style.ERROR(
                    'Password is required. Set DJANGO_SUPERUSER_PASSWORD environment variable '
                    'or use --password flag.'
                )
            )
            return

        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superuser "{username}"')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
