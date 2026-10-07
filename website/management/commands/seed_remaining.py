import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db.models import Q
from website.models import ContentBlock, ContentPage


class Command(BaseCommand):
    help = 'Add the remaining reference page content, preserving existing edited records.'

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[2] / 'data'
        for row in json.loads((root / 'remaining_pages.json').read_text()):
            blocks = row.pop('blocks')
            slug = row.pop('slug')
            page, _ = ContentPage.objects.get_or_create(slug=slug, defaults=row)
            for block in blocks:
                exists = page.blocks.filter(Q(title=block['title']) | Q(translations__nl__title=block['title'])).exists()
                if not exists:
                    ContentBlock.objects.create(page=page, **block)
        if (root / 'vacancy.json').exists():
            row = json.loads((root / 'vacancy.json').read_text())
            ContentPage.objects.get_or_create(slug=row.pop('slug'), defaults=row)
        self.stdout.write(self.style.SUCCESS('Remaining page content is ready.'))
