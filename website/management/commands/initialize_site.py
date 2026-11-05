"""Initialize a fresh deployment and copy its public media onto persistent storage."""
import os
from pathlib import Path
import shutil
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import BlogPost, ContentPage, SiteSettings, TeamMember


class Command(BaseCommand):
    help = 'Initialize a fresh deployment from the public content snapshot, without overwriting admin edits.'

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[2] / 'data'
        target = Path(settings.MEDIA_ROOT)
        target.mkdir(parents=True, exist_ok=True)
        for source in (root / 'initial_media').rglob('*'):
            if source.is_file():
                destination = target / source.relative_to(root / 'initial_media')
                if not destination.exists():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
        initialized = any(model.objects.exists() for model in (SiteSettings, TeamMember, ContentPage, BlogPost))
        if not initialized:
            with transaction.atomic():
                call_command('loaddata', str(root / 'deployment_content.json'), verbosity=0)
            self.stdout.write(self.style.SUCCESS('Initial public website content loaded.'))
        else:
            self.stdout.write('Existing website content preserved.')
        call_command('seed_practice_details')
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        if username and password:
            user_model = get_user_model()
            if not user_model.objects.filter(username=username).exists():
                user_model.objects.create_superuser(username=username,
                    email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''), password=password)
                self.stdout.write(self.style.SUCCESS('Initial administrator created.'))
