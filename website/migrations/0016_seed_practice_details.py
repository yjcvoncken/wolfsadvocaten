"""Restore the original sections and photographs on existing installations."""
import json
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations


def seed_details(apps, schema_editor):
    root = Path(__file__).resolve().parents[1] / 'data'
    Area = apps.get_model('website', 'PracticeArea')
    Section = apps.get_model('website', 'PracticeAreaSection')
    database = schema_editor.connection.alias
    originals = {title: body for kind, title, body in json.loads((root / 'profiles.json').read_text())
                 if kind == 'area'}
    original_dutch = {item['fields']['slug']: item['fields'].get('translations', {}).get('nl', {}).get('body', '')
                      for item in json.loads((root / 'deployment_content.json').read_text())
                      if item['model'] == 'website.practicearea'}
    normalize = lambda value: ' '.join(value.split())
    for entry in json.loads((root / 'practice_details.json').read_text()):
        area = Area.objects.using(database).filter(slug=entry['slug']).first()
        if not area or Section.objects.using(database).filter(area=area).exists():
            continue
        # Preserve customized article bodies instead of hiding them behind the reference text.
        if normalize(area.body) != normalize(originals.get(area.title, '')):
            continue
        dutch = area.translations.get('nl', {}).get('body', '')
        if dutch and normalize(dutch) != normalize(original_dutch.get(area.slug, '')):
            continue
        for field in ('detail_image', 'secondary_image'):
            if not getattr(area, field):
                name = entry[field]
                if not default_storage.exists(name):
                    with (root / 'initial_media' / name).open('rb') as image:
                        name = default_storage.save(name, File(image))
                setattr(area, field, name)
        area.save(using=database, update_fields=['detail_image', 'secondary_image'])
        for section in entry['sections']:
            Section.objects.using(database).create(area=area, **section)


class Migration(migrations.Migration):
    dependencies = [('website', '0015_practice_detail_sections')]
    operations = [migrations.RunPython(seed_details, migrations.RunPython.noop)]
