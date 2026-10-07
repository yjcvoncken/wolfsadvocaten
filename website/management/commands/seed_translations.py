"""Install initial translations without replacing text edited in admin."""
import hashlib
import json
from pathlib import Path
import shutil
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Load English/Dutch content translations, preserving existing translations and source edits.'

    @transaction.atomic
    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[2] / 'data'
        changed = 0
        for record in json.loads((root / 'translations.json').read_text()):
            model = apps.get_model('website', record['model'])
            obj = model.objects.filter(**record['lookup']).first()
            if not obj:
                continue
            translations = obj.translations or {}
            dutch = translations.setdefault('nl', {})
            dirty = False
            for field, translation in record['nl'].items():
                source_hash = hashlib.sha256(getattr(obj, field).encode()).hexdigest()
                if source_hash != record['source'][field] or field in dutch:
                    continue
                dutch[field] = translation
                dirty = True
            for field, translation in record.get('en', {}).items():
                source_hash = hashlib.sha256(getattr(obj, field).encode()).hexdigest()
                if source_hash == record['source'][field]:
                    setattr(obj, field, translation)
                    dirty = True
            if dirty:
                obj.translations = translations
                obj.save()
                changed += 1
        model = apps.get_model('website', 'ContentPage')
        for slug in ('terms-and-conditions', 'privacy-statement'):
            page = model.objects.filter(slug=slug).first()
            if page and not page.document_nl:
                filename = f'{slug}-nl.pdf'
                destination = Path(settings.MEDIA_ROOT) / 'documents' / filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / 'legal_documents' / filename, destination)
                page.document_nl = f'documents/{filename}'
                page.save(update_fields=['document_nl'])
        self.stdout.write(self.style.SUCCESS(f'Translations loaded for {changed} records.'))
