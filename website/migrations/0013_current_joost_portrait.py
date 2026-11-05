"""Use the current public portrait while retaining custom admin uploads."""
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations


def update_portrait(apps, schema_editor):
    members = apps.get_model('website', 'TeamMember').objects.using(schema_editor.connection.alias)
    matches = members.filter(name__iexact='Joost van den Akker', photo__in=(
        'team/joost.jpg', 'team/joost-van-den-akker-reference-20261021.png',
    ))
    if not matches.exists():
        return
    name = 'team/joost-van-den-akker-current-20261105.jpg'
    if not default_storage.exists(name):
        source = Path(__file__).resolve().parents[1] / 'data' / 'initial_media' / name
        with source.open('rb') as portrait:
            name = default_storage.save(name, File(portrait))
    matches.update(photo=name)


class Migration(migrations.Migration):
    dependencies = [('website', '0012_current_team_photos')]
    operations = [migrations.RunPython(update_portrait, migrations.RunPython.noop)]
