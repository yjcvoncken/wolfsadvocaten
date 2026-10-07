import json
from pathlib import Path
from django.core.management.base import BaseCommand
from website.models import ContentPage


class Command(BaseCommand):
    help = 'Add original legal pages and PDF links without replacing admin edits.'

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[2] / 'data'
        for row in json.loads((root / 'legal_pages.json').read_text()):
            slug = row.pop('slug')
            ContentPage.objects.get_or_create(slug=slug, defaults=row)
        for slug, title in [('terms-and-conditions', 'Terms & conditions'), ('privacy-statement', 'Privacy statement')]:
            ContentPage.objects.get_or_create(slug=slug, defaults={
                'title': title, 'body': '', 'document': f'documents/{slug}.pdf'})
        self.stdout.write(self.style.SUCCESS('Legal pages are ready.'))
