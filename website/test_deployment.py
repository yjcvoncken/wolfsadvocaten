from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from .models import BlogPost, ContentPage, SiteSettings, TeamMember


class DeploymentTests(TestCase):
    def test_fresh_deployment_restores_public_content_and_preserves_later_edits(self):
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            call_command('initialize_site', stdout=StringIO())
            self.assertEqual(BlogPost.objects.count(), 114)
            self.assertTrue(SiteSettings.objects.exists())
            self.assertFalse(TeamMember.objects.filter(published=False).exists())
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
                self.assertEqual(self.client.get(path).status_code, 200)

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
