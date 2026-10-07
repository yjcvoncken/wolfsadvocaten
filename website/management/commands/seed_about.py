import json
from pathlib import Path
from django.core.management.base import BaseCommand
from website.models import AboutSection, TeamMember


class Command(BaseCommand):
    help = 'Add the About us reference content without replacing edits in the admin.'

    def handle(self, *args, **options):
        records = json.loads((Path(__file__).resolve().parents[2] / 'data/about_sections.json').read_text())
        for record in records:
            key = record.pop('key')
            AboutSection.objects.get_or_create(key=key, defaults=record)
        for name, role, image, order in [
            ('Luna van de Ven', 'Paralegal', 'about/luna.jpg', 5),
            ('Shania Huininga', 'Accounting', 'about/shania.jpg', 7),
        ]:
            TeamMember.objects.get_or_create(name=name, defaults={
                'role': role, 'email': 'info@wolfsadvocaten.nl',
                'phone': '+31 (0)85 079 97 50', 'photo': image,
                'order': order, 'show_on_home': False, 'show_on_about': True,
            })
        self.stdout.write(self.style.SUCCESS('About us content is ready.'))
