from .seo import original_path
from io import StringIO
from importlib import import_module
from types import SimpleNamespace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from .models import BlogPost, ContentPage, SiteSettings, TeamMember


class DeploymentTests(TestCase):
    def test_production_domain_works_without_railway_domain_variables(self):
        import os
        import runpy
        from unittest.mock import patch
        ContentPage.objects.create(slug='vacancies', title='Vacancies', published=True)
        environment = {
            'DJANGO_DEBUG': '0', 'DJANGO_SECRET_KEY': 'test-only-secret',
            'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1',
        }
        with patch.dict(os.environ, environment, clear=True):
            config = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'config/settings.py'))
        domain = 'wolfsadvocaten-production.up.railway.app'
        self.assertIn(domain, config['ALLOWED_HOSTS'])
        self.assertNotIn('*', config['ALLOWED_HOSTS'])
        self.assertNotIn('.up.railway.app', config['ALLOWED_HOSTS'])
        with self.settings(ALLOWED_HOSTS=config['ALLOWED_HOSTS'], DEBUG=False):
            for path in ('/vacancies/', '/nl/vacancies/'):
                self.assertEqual(self.client.get(original_path(path), HTTP_HOST=domain, secure=True).status_code, 200)
            self.assertEqual(self.client.get('/vacancies/', HTTP_HOST='unrelated.up.railway.app', secure=True).status_code, 400)

    def test_portrait_upgrade_updates_existing_database_and_copies_media(self):
        member = TeamMember.objects.create(name='John Wolfs', role='Edited role', photo='team/old.jpg')
        other = TeamMember.objects.create(name='Custom member', photo='team/custom.jpg')
        migration = import_module('website.migrations.0012_current_team_photos')
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            migration.update_portraits(apps, SimpleNamespace(connection=connection))
            member.refresh_from_db()
            other.refresh_from_db()
            self.assertEqual(member.photo.name, 'team/john-wolfs-reference-20261021.jpg')
            self.assertEqual(member.role, 'Edited role')
            self.assertEqual(other.photo.name, 'team/custom.jpg')
            self.assertEqual(TeamMember.objects.count(), 2)
            bundled = Path(__file__).parent / 'data' / 'initial_media' / member.photo.name
            self.assertEqual((Path(directory) / member.photo.name).read_bytes(), bundled.read_bytes())

    def test_snapshot_strings_fit_database_columns(self):
        snapshot = Path(__file__).parent / 'data' / 'deployment_content.json'
        for record in json.loads(snapshot.read_text()):
            model = apps.get_model(record['model'])
            for name, value in record['fields'].items():
                field = model._meta.get_field(name)
                if isinstance(value, str) and getattr(field, 'max_length', None):
                    with self.subTest(model=record['model'], pk=record['pk'], field=name):
                        self.assertLessEqual(len(value), field.max_length)

    def test_fresh_deployment_restores_public_content_and_preserves_later_edits(self):
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            call_command('initialize_site', stdout=StringIO())
            self.assertEqual(BlogPost.objects.count(), 114)
            self.assertTrue(SiteSettings.objects.exists())
            self.assertFalse(TeamMember.objects.filter(published=False).exists())
            about_names = set(TeamMember.objects.filter(show_on_about=True).values_list('name', flat=True))
            self.assertTrue({
                'John Wolfs', 'Maurice van Efferink', 'Joost van den Akker', 'Menno van Term',
                'Ella Delanty', 'Romy Brüll', 'Vera Ubaghs',
            }.issubset(about_names))
            self.assertFalse(about_names.intersection({'Ron Meulmeester', 'Bas Janssen', 'Gino di Antonio'}))
            self.assertFalse(get_user_model().objects.exists())
            site = SiteSettings.objects.first()
            self.assertTrue(Path(site.hero_image.path).is_file())
            original_media = Path(site.hero_image.path)
            original_media.write_bytes(b'Keep replacement media')
            site.tagline = 'Edited in production'
            site.save()
            count = TeamMember.objects.count()
            call_command('initialize_site', stdout=StringIO())
            self.assertEqual(SiteSettings.objects.first().tagline, 'Edited in production')
            self.assertEqual(TeamMember.objects.count(), count)
            self.assertEqual(original_media.read_bytes(), b'Keep replacement media')
            for path in ('/', '/nl/', '/vacancies/', '/nl/vacancies/'):
                self.assertEqual(self.client.get(original_path(path)).status_code, 200)

    def test_existing_partial_site_is_not_overwritten(self):
        SiteSettings.objects.create(tagline='My existing website')
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            call_command('initialize_site', stdout=StringIO())
        self.assertEqual(SiteSettings.objects.first().tagline, 'My existing website')
        self.assertEqual(BlogPost.objects.count(), 0)

    def test_media_is_served_with_debug_disabled_and_cannot_escape_upload_directory(self):
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory, DEBUG=False):
            image = Path(directory) / 'photo.png'
            image.write_bytes(b'photo bytes')
            response = self.client.get('/media/photo.png')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'photo bytes')
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(self.client.get('/media/../config/settings.py').status_code, 404)
            self.assertEqual(self.client.get('/media/missing.jpg').status_code, 404)
            self.assertEqual(self.client.post('/media/photo.png').status_code, 405)

    def test_healthcheck(self):
        self.assertEqual(self.client.get('/healthz/').json(), {'status': 'ok'})
