"""Install the reference portraits once, including on existing deployments."""
import json
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations


def update_portraits(apps, schema_editor):
    root = Path(__file__).resolve().parents[1] / 'data'
    portraits = json.loads((root / 'team_photos_20261021.json').read_text())
    members = apps.get_model('website', 'TeamMember').objects.using(schema_editor.connection.alias)
    for portrait in portraits:
        matches = members.filter(name__iexact=portrait['name'])
        if not matches.exists():
            continue
        name = portrait['photo']
        # New versioned filenames avoid cached old portraits and preserve old uploads.
        if not default_storage.exists(name):
            with (root / 'initial_media' / name).open('rb') as source:
                name = default_storage.save(name, File(source))
        matches.update(photo=name)


class Migration(migrations.Migration):
    dependencies = [('website', '0011_extend_media_path_lengths')]
    operations = [migrations.RunPython(update_portraits, migrations.RunPython.noop)]
