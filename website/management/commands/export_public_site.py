"""Export publishable site content without users, credentials or contact submissions."""
from pathlib import Path
import shutil
from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db.models import FileField
from website.models import AboutSection, BlogPost, ContentBlock, ContentPage, PracticeArea, SitePhoto, SiteSettings, TeamMember


class Command(BaseCommand):
    help = 'Export current published website content and referenced media for a fresh deployment.'

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[2] / 'data'
        collections = [SiteSettings.objects.all(), SitePhoto.objects.all(),
            TeamMember.objects.filter(published=True), PracticeArea.objects.filter(published=True),
            BlogPost.objects.filter(published=True), ContentPage.objects.filter(published=True),
            AboutSection.objects.filter(published=True),
            ContentBlock.objects.filter(published=True, page__published=True)]
        objects = [obj for collection in collections for obj in collection]
        files = {'site/contact.jpg'}
        for obj in objects:
            for field in obj._meta.fields:
                if isinstance(field, FileField):
                    value = getattr(obj, field.name)
                    if value:
                        files.add(value.name)
        bundle = root / 'initial_media'
        for name in sorted(files):
            source = (Path(settings.MEDIA_ROOT) / name).resolve()
            if not source.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not source.is_file():
                raise CommandError(f'Referenced public media file is missing: {name}')
            destination = bundle / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        (root / 'deployment_content.json').write_text(serializers.serialize('json', objects,
            indent=2, ensure_ascii=False)+'\n')
        self.stdout.write(self.style.SUCCESS(f'Exported {len(objects)} public content records and {len(files)} referenced media files.'))
