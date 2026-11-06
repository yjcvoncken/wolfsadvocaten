"""Check the new application against the captured original public URL inventory."""
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html

from website.seo import inventory


class Command(BaseCommand):
    help = 'Verify original URLs and SEO metadata against the current local/production database, without changing DNS.'

    def handle(self, *args, **options):
        client = Client(raise_request_exception=False)
        failures = []
        pages = redirects = 0
        for path, record in inventory()['pages'].items():
            response = client.get(path, secure=True, HTTP_HOST='www.wolfsadvocaten.nl')
            if record['status'] != 200:
                if response.status_code != 404:
                    failures.append(f'{path}: expected original 404, got {response.status_code}')
            elif record.get('redirect'):
                redirects += 1
                if response.status_code != 301 or response.url != iri_to_uri(record['redirect']):
                    failures.append(f'{path}: original redirect missing or different')
            else:
                pages += 1
                if response.status_code != 200:
                    failures.append(f'{path}: expected 200, got {response.status_code}')
                    continue
                expected = (
                    format_html('<title>{}</title>', record['title']),
                    format_html('<meta name="description" content="{}">', record['description']),
                    format_html('<link rel="canonical" href="{}">', record['canonical']),
                )
                if any(str(value).encode() not in response.content for value in expected):
                    failures.append(f'{path}: original SEO metadata differs')
        for path in inventory()['files']:
            response = client.get(path, secure=True, HTTP_HOST='www.wolfsadvocaten.nl')
            if response.status_code != 200 or response.get('Content-Type') != 'application/pdf':
                failures.append(f'{path}: original PDF unavailable')
            response.close()
        if failures:
            raise CommandError('\n'.join(failures))
        self.stdout.write(self.style.SUCCESS(
            f'Verified {pages} original pages, {redirects} original redirects and 4 PDF paths. '
            'Original titles, descriptions and canonical URLs match.'))
