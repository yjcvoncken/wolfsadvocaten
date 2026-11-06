from datetime import date
from io import StringIO
from html.parser import HTMLParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html
from django.utils.translation import activate, get_language, override

from .models import BlogPost, ContentPage, PracticeArea, TeamMember
from .seo import inventory, original_path


@override_settings(PUBLIC_SITE_ORIGIN='https://www.wolfsadvocaten.nl')
class OriginalSEOTests(TestCase):
    def setUp(self):
        language = get_language()
        activate('en')
        self.addCleanup(activate, language)

    def make_post(self):
        slug = 'eu-adopts-16th-sanctions-package-against-russia'
        return BlogPost.objects.create(title='Article title', slug=slug, body='English article body',
                                       published_at=date.today(), published=True,
                                       translations={'nl': {'title': 'Nederlandse titel', 'body': 'Nederlandse artikeltekst'}})

    def test_all_captured_urls_keep_original_metadata_or_redirect_status(self):
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            call_command('initialize_site', stdout=StringIO())
            for path, record in inventory()['pages'].items():
                with self.subTest(path=path):
                    response = self.client.get(path)
                    if record['status'] != 200:
                        self.assertEqual(response.status_code, 404)
                    elif record.get('redirect'):
                        self.assertEqual(response.status_code, 301)
                        self.assertEqual(response.url, iri_to_uri(record['redirect']))
                    else:
                        self.assertEqual(response.status_code, 200)
                        self.assertContains(response, format_html('<title>{}</title>', record['title']))
                        self.assertContains(response, format_html('<meta name="description" content="{}">', record['description']))
                        self.assertContains(response, format_html('<link rel="canonical" href="{}">', record['canonical']))
                        for alternate in record.get('alternates', []):
                            self.assertContains(response, format_html(
                                '<link rel="alternate" hreflang="{}" href="{}">',
                                alternate['hreflang'], alternate['href']))
                        if record.get('robots'):
                            self.assertContains(response, format_html('<meta name="robots" content="{}">', record['robots']))

    def test_structured_data_remains_equivalent_to_the_original(self):
        self.make_post()

        class StructuredDataParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.active = False
                self.parts = []
                self.records = []

            def handle_starttag(self, tag, attrs):
                if tag == 'script' and dict(attrs).get('type') == 'application/ld+json':
                    self.active = True
                    self.parts = []

            def handle_data(self, text):
                if self.active:
                    self.parts.append(text)

            def handle_endtag(self, tag):
                if tag == 'script' and self.active:
                    self.records.append(json.loads(''.join(self.parts)))
                    self.active = False

        for path in ('/', '/post/eu-adopts-16th-sanctions-package-against-russia'):
            parser = StructuredDataParser()
            parser.feed(self.client.get(path).content.decode())
            self.assertEqual(parser.records, inventory()['pages'][path]['structured_data'])

    def test_old_blog_urls_dutch_slugs_and_new_aliases(self):
        post = self.make_post()
        en = '/post/eu-adopts-16th-sanctions-package-against-russia'
        nl = '/nl/post/16e-sanctiepakket-rusland'
        self.assertEqual(post.get_absolute_url(), en)
        with override('nl'):
            self.assertEqual(post.get_absolute_url(), nl)
        self.assertContains(self.client.get(en), 'English article body')
        self.assertContains(self.client.get(nl), 'Nederlandse artikeltekst')
        for alias, target in ((f'/blog/{post.slug}/', en), (f'/nl/blog/{post.slug}/', nl), (en + '/', en), (nl + '/', nl)):
            self.assertRedirects(self.client.get(alias), target, status_code=301)
        post.published = False
        post.save()
        self.assertEqual(self.client.get(en).status_code, 404)
        self.assertEqual(self.client.get(nl).status_code, 404)

    def test_legacy_practice_and_profile_links_and_language_switch(self):
        area = PracticeArea.objects.create(title='Customs law', slug='customs-law', body='Customs content')
        member = TeamMember.objects.create(name='Joost van den Akker', role='Jurist')
        self.assertEqual(area.get_absolute_url(), '/customs')
        self.assertEqual(member.get_absolute_url(), '/joost-vanden-akker')
        self.assertRedirects(self.client.get('/practice-areas/customs-law/'), '/customs', status_code=301)
        self.assertRedirects(self.client.get('/joost-van-den-akker/'), '/joost-vanden-akker', status_code=301)
        post = self.make_post()
        response = self.client.post('/i18n/setlang/', {'language': 'nl', 'next': post.get_absolute_url() + '?utm_source=test'})
        self.assertEqual(response.url, '/nl/post/16e-sanctiepakket-rusland?utm_source=test')
        response = self.client.post('/i18n/setlang/', {'language': 'en', 'next': response.url})
        self.assertEqual(response.url, post.get_absolute_url() + '?utm_source=test')

    def test_pagination_redirects_once_and_keeps_tracking_query(self):
        for number in range(7):
            BlogPost.objects.create(title=f'News {number}', body='Body', published=True, published_at=date.today())
        self.assertRedirects(self.client.get('/blog/?page=2&utm_source=test'),
                             '/blog/page/2?utm_source=test', status_code=301)
        self.assertRedirects(self.client.get('/blog/page/1'), '/blog', status_code=301)
        self.assertRedirects(self.client.get('/blog?page=' + '9' * 5000), '/blog', status_code=301)
        response = self.client.get('/blog/page/2')
        self.assertEqual(len(response.context['posts']), 1)
        self.assertContains(response, 'href="/blog"')
        self.assertEqual(self.client.get('/blog/page/20').status_code, 404)

    def test_original_pdf_urls_and_administrator_replacements(self):
        from django.core.files.base import ContentFile
        root = Path(__file__).parent / 'data/legal_documents'
        with TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            for path in inventory()['files']:
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/pdf')
                self.assertEqual(b''.join(response.streaming_content), (root / path.rsplit('/', 1)[-1]).read_bytes())
            page = ContentPage.objects.create(title='Terms', slug='terms-and-conditions')
            page.document.save('updated.pdf', ContentFile(b'%PDF replacement from admin'), save=True)
            response = self.client.get('/_files/ugd/bff2b6_b7db59421ef44bf9a68f409ebc1a2547.pdf')
            self.assertEqual(b''.join(response.streaming_content), b'%PDF replacement from admin')

    def test_sitemaps_and_preview_indexing_are_safe(self):
        post = self.make_post()
        for filename in inventory()['sitemaps']:
            response = self.client.get('/' + filename)
            self.assertEqual(response.status_code, 200)
            ET.fromstring(response.content)
        response = self.client.get('/blog-posts-sitemap.xml')
        self.assertContains(response, 'https://www.wolfsadvocaten.nl' + post.get_absolute_url())
        post.published = False
        post.save()
        self.assertNotContains(self.client.get('/blog-posts-sitemap.xml'), '/post/' + post.slug)
        self.assertNotContains(self.client.get('/nl_nl-blog-posts-sitemap.xml'), '16e-sanctiepakket-rusland')
        preview = self.client.get('/', HTTP_HOST='wolfsadvocaten-production.up.railway.app', secure=True)
        self.assertEqual(preview['X-Robots-Tag'], 'noindex, follow')
        self.assertContains(preview, '<link rel="canonical" href="https://www.wolfsadvocaten.nl">')
        primary = self.client.get('/', HTTP_HOST='www.wolfsadvocaten.nl', secure=True)
        self.assertFalse(primary.has_header('X-Robots-Tag'))
        self.assertRedirects(self.client.get('/blog/?page=2', HTTP_HOST='wolfsadvocaten.nl', secure=True),
                             'https://www.wolfsadvocaten.nl/blog/page/2', status_code=301, fetch_redirect_response=False)
        self.assertEqual(self.client.get('/robots.txt')['Content-Type'], 'text/plain; charset=utf-8')

    def test_new_posts_use_original_convention_and_join_both_sitemaps(self):
        post = BlogPost.objects.create(title='A new article', body='Article body', published=True, published_at=date.today())
        self.assertEqual(post.get_absolute_url(), '/post/a-new-article')
        self.assertContains(self.client.get(post.get_absolute_url()), 'Article body')
        self.assertRedirects(self.client.get('/post/a-new-article/'), '/post/a-new-article', status_code=301)
        self.assertContains(self.client.get('/blog-posts-sitemap.xml'), 'https://www.wolfsadvocaten.nl/post/a-new-article')
        self.assertContains(self.client.get('/nl_nl-blog-posts-sitemap.xml'), 'https://www.wolfsadvocaten.nl/nl/post/a-new-article')
        BlogPost.objects.bulk_create([
            BlogPost(title=f'Additional article {number}', slug=f'additional-article-{number}',
                     body='Article body', published=True, published_at=date.today())
            for number in range(114)
        ])
        response = self.client.get('/blog/page/20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['posts']), 1)
        self.assertContains(response, '<link rel="canonical" href="https://www.wolfsadvocaten.nl/blog/page/20">')

    def test_archived_pages_remain_editable_without_resurrecting_hidden_content(self):
        path = '/managementassistent-juridisch-secretaresse'
        self.assertEqual(self.client.get(path).status_code, 200)
        page = ContentPage.objects.create(slug=path[1:], title='Edited vacancy', body='Current vacancy content')
        self.assertContains(self.client.get(path), page.body)
        page.published = False
        page.save()
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertNotContains(self.client.get('/pages-sitemap.xml'), path)

    def test_url_normalization_cannot_redirect_to_an_external_host(self):
        for path in ('/%2Fexample.com', '/%5Cexample.com', '//example.com', 'https://example.com/'):
            self.assertEqual(original_path(path), path)
        for path in ('/%2Fexample.com', '/%5Cexample.com'):
            response = self.client.get(path)
            self.assertNotIn(response.get('Location', ''), ('//example.com', 'https://example.com/'))


@override_settings(PUBLIC_SITE_ORIGIN='https://wolfsadvocaten-production.up.railway.app')
class RailwayOriginTests(TestCase):
    def test_railway_host_changes_without_changing_original_subpaths(self):
        origin = 'https://wolfsadvocaten-production.up.railway.app'
        response = self.client.get('/')
        self.assertContains(response, f'<link rel="canonical" href="{origin}">')
        self.assertNotContains(response, 'href="https://www.wolfsadvocaten.nl')
        self.assertContains(self.client.get('/robots.txt'), origin + '/sitemap.xml')
        self.assertContains(self.client.get('/sitemap.xml'), origin + '/pages-sitemap.xml')
        self.assertContains(self.client.get('/nl'), f'href="{origin}/nl"')
        post = BlogPost.objects.create(
            title='Article', body='English content', published=True, published_at=date.today(),
            slug='eu-adopts-16th-sanctions-package-against-russia',
            translations={'nl': {'body': 'Nederlandse inhoud'}},
        )
        english = '/post/eu-adopts-16th-sanctions-package-against-russia'
        with override('en'):
            self.assertEqual(post.get_absolute_url(), english)
        response = self.client.get('/nl/post/16e-sanctiepakket-rusland')
        self.assertContains(response, 'Nederlandse inhoud')
        self.assertContains(response, f'href="{origin}/nl/post/16e-sanctiepakket-rusland"')
        self.assertNotContains(response, 'href="https://www.wolfsadvocaten.nl')
        self.assertRedirects(self.client.get('/blog/' + post.slug + '/'), english, status_code=301)
        self.assertContains(self.client.get('/blog-posts-sitemap.xml'), origin + english)
