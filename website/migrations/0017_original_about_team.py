from django.db import migrations


def restore_about_team(apps, schema_editor):
    members = apps.get_model('website', 'TeamMember').objects.using(schema_editor.connection.alias)
    members.filter(name__in=(
        'John Wolfs', 'Maurice van Efferink', 'Joost van den Akker', 'Menno van Term',
        'Ella Delanty', 'Romy Brüll', 'Vera Ubaghs',
    )).update(show_on_about=True)
    members.filter(name__in=('Ron Meulmeester', 'Bas Janssen', 'Gino di Antonio')).update(show_on_about=False)


class Migration(migrations.Migration):
    dependencies = [('website', '0016_seed_practice_details')]
    operations = [migrations.RunPython(restore_about_team, migrations.RunPython.noop)]
