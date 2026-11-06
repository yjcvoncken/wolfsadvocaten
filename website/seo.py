"""Original public URLs and SEO metadata, captured before the hosting migration."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.utils.encoding import iri_to_uri
from django.utils.translation import get_language


@lru_cache(maxsize=1)
def _source_inventory():
    return json.loads((Path(__file__).parent / 'data/legacy_seo.json').read_text())


@lru_cache(maxsize=4)
def _inventory_for_origin(origin):
    source = _source_inventory()
    original = source['origin']

    def adapt(value):
        if isinstance(value, str) and (value == original or value.startswith(tuple(original + suffix for suffix in ('/', '#', '?')))):
            return origin + value[len(original):]
        if isinstance(value, dict):
            return {key: adapt(item) for key, item in value.items()}
        if isinstance(value, list):
            return [adapt(item) for item in value]
        return value

    return adapt(source)


def inventory():
    origin = (getattr(settings, 'PUBLIC_SITE_ORIGIN', None) or os.environ.get(
        'DJANGO_PUBLIC_ORIGIN', 'https://wolfsadvocaten-production.up.railway.app')).rstrip('/')
    parts = urlsplit(origin)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.path or parts.query or parts.fragment:
        raise ImproperlyConfigured('DJANGO_PUBLIC_ORIGIN must be a website origin, such as https://example.com.')
    return _inventory_for_origin(origin)


def original_path(url):
    """Convert an internal route to its original public path, preserving query/fragment."""
    if not url or not url.startswith('/') or url.startswith('//'):
        return url
    parts = urlsplit(url)
    path = unquote(parts.path) or '/'
    if path.startswith('//') or '\\' in path:
        return url
    aliases = inventory()['aliases']
    recognized = path in aliases or path in inventory()['pages'] or re.fullmatch(r'/(?:nl/)?post/[^/]+/?', path)
    recognized = recognized or re.fullmatch(r'/(?:nl/)?blog/(?:categories|tags)/[^/]+/page/[1-9]\d*/?', path)
    recognized = recognized or re.fullmatch(r'/(?:nl/)?blog/page/[1-9]\d*/?', path)
    if not recognized:
        return url
    seen = set()
    while path not in seen:
        destination = aliases.get(path) or inventory()['pages'].get(path, {}).get('redirect')
        if not destination:
            break
        seen.add(path)
        path = destination
    if re.fullmatch(r'/(?:nl/)?post/[^/]+/', path):
        path = path.rstrip('/')
    if re.fullmatch(r'/(?:nl/)?blog/(?:categories|tags)/[^/]+/page/[1-9]\d*/', path):
        path = path.rstrip('/')
    if re.fullmatch(r'/(?:nl/)?blog/page/[1-9]\d*/', path):
        path = path.rstrip('/')
    if path.endswith('/page/1') and ('/blog/page/' in path or '/blog/categories/' in path or '/blog/tags/' in path):
        path = path[:-7]
    query = parse_qsl(parts.query, keep_blank_values=True)
    page = next((value for key, value in query if key == 'page'), None)
    archive = path in inventory()['pages'] and (
        path in ('/blog', '/nl/blog') or inventory()['pages'][path].get('handler') == 'archive')
    if archive and page is not None:
        value = page.strip()
        number = int(value) if value.isdecimal() and len(value) <= 6 else 1
        number = max(1, number)
        query = [(key, value) for key, value in query if key != 'page']
        if number > 1:
            path += '/page/' + str(number)
    return urlunsplit(('', '', path, urlencode(query), parts.fragment))


def model_path(group, key, fallback):
    language = (get_language() or 'en').split('-')[0]
    known = inventory()['model_paths'].get(group, {}).get(key, {}).get(language)
    if known:
        return known
    if group == 'posts':
        return ('/nl' if language == 'nl' else '') + '/post/' + key
    return original_path(fallback)


def translated_path(url, language):
    parts = urlsplit(original_path(url))
    if parts.netloc or parts.scheme or not parts.path.startswith('/'):
        return url
    record = inventory()['pages'].get(unquote(parts.path))
    if record:
        for alternate in record.get('alternates', []):
            if alternate.get('hreflang', '').split('-')[0] == language:
                return urlunsplit(('', '', urlsplit(alternate['href']).path or '/', parts.query, parts.fragment))
        if record.get('handler') == 'post':
            target = inventory()['model_paths']['posts'][record['key']].get(language)
            if target:
                return urlunsplit(('', '', target, parts.query, parts.fragment))
    path = parts.path
    if path == '/nl':
        path = '/'
    elif path.startswith('/nl/'):
        path = path[3:]
    if language == 'nl':
        path = '/nl' + (path if path != '/' else '')
    return original_path(urlunsplit(('', '', path, parts.query, parts.fragment)))


def page_record(path):
    record = inventory()['pages'].get(path)
    if record:
        return record
    post_match = re.fullmatch(r'(/nl)?/post/([^/]+)', path)
    if post_match:
        from .models import BlogPost
        from .localization import localized
        from django.utils.translation import override
        post = BlogPost.objects.filter(slug=post_match[2]).first()
        if not post or not post.published:
            return {'status': 404}
        language = 'nl' if post_match[1] else 'en'
        with override(language):
            title = localized(post, 'title')
            description = localized(post, 'excerpt') or localized(post, 'body')[:160]
        return {'status': 200, 'handler': 'post', 'key': post.slug,
                'internal': (post_match[1] or '') + '/post/' + post.slug + '/',
                'title': title, 'description': description,
                'canonical': inventory()['origin'] + path, 'alternates': []}
    blog_match = re.fullmatch(r'(/nl)?/blog/page/([1-9]\d*)', path)
    if blog_match:
        from .models import BlogPost
        if len(blog_match[2]) > 6:
            return {'status': 404}
        number = int(blog_match[2])
        total = max(1, (BlogPost.objects.filter(published=True).count() + 5) // 6)
        if number > total:
            return {'status': 404}
        prefix = blog_match[1] or ''
        base = inventory()['pages'][prefix + '/blog']
        title = base['title'] + f' | Page {number} of {total}'
        canonical = inventory()['origin'] + path
        metadata = []
        for tag in base.get('meta', []):
            name = tag.get('property') or tag.get('name')
            value = title if name in ('og:title', 'twitter:title') else (
                canonical if name in ('og:url', 'twitter:url') else tag['content'])
            metadata.append({**tag, 'content': value})
        return {**base, 'handler': 'blog', 'page': number, 'internal': prefix + '/blog/',
                'title': title, 'canonical': canonical, 'meta': metadata, 'structured_data': [],
                'alternates': [
                    {'hreflang': 'en-us', 'href': inventory()['origin'] + '/blog/page/' + str(number)},
                    {'hreflang': 'nl-nl', 'href': inventory()['origin'] + '/nl/blog/page/' + str(number)},
                ]}
    match = re.fullmatch(r'(.+/blog/(?:categories|tags)/[^/]+)/page/([1-9]\d*)', path)
    # The English form starts with /blog, with no language segment.
    if not match:
        match = re.fullmatch(r'(/blog/(?:categories|tags)/[^/]+)/page/([1-9]\d*)', path)
    if match:
        base = inventory()['pages'].get(match[1])
        if base and base.get('handler') == 'archive':
            if len(match[2]) > 6:
                return {'status': 404}
            return {**base, 'page': int(match[2]), 'canonical': inventory()['origin'] + path,
                    'title': base['title'] + f' | Page {match[2]}', 'alternates': []}
    return None


class LegacyURLMiddleware:
    """Serve original paths using existing views; redirect only alternate public paths."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':', 1)[0].lower()
        if host == 'wolfsadvocaten.nl' and request.method in ('GET', 'HEAD'):
            return HttpResponsePermanentRedirect(inventory()['origin'] + original_path(request.get_full_path()))
        path = unquote(request.path_info)
        excluded = path.startswith(('/admin/', '/static/', '/media/', '/i18n/', '/_files/', '/nl/_files/'))
        excluded = excluded or path == '/healthz/' or path.endswith(('.xml', '.txt', '.ico'))
        if not excluded:
            target = original_path(request.get_full_path())
            if request.method in ('GET', 'HEAD') and iri_to_uri(target) != request.get_full_path():
                return HttpResponsePermanentRedirect(target)
            record = page_record(path)
            if record and record.get('status') != 200:
                from django.views.defaults import page_not_found
                return page_not_found(request, Http404())
            if record and record.get('redirect'):
                destination = record['redirect']
                if request.META.get('QUERY_STRING'):
                    destination += '?' + request.META['QUERY_STRING']
                return HttpResponsePermanentRedirect(destination)
            request.legacy_seo = record
            if record and record.get('status') == 200:
                request.path_info = record['internal']
        # The actual public host is configurable; Railway remains usable before DNS cutover.
        response = self.get_response(request)
        if host.endswith('.up.railway.app'):
            response['X-Robots-Tag'] = 'noindex, follow'
        return response


def seo_context(request):
    record = getattr(request, 'legacy_seo', None)
    if record and record.get('status') == 200:
        structured = [mark_safe(json.dumps(item, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))
                      for item in record.get('structured_data', [])]
        return {'seo': {**record, 'structured_json': structured}}
    path = original_path(request.path)
    return {'seo': {'canonical': inventory()['origin'] + path}}


def legacy_page(request, legacy_path=None):
    record = getattr(request, 'legacy_seo', None)
    if not record or record.get('status') != 200:
        raise Http404
    from .views import context
    if record.get('handler') == 'archive':
        from .models import BlogPost
        from django.core.paginator import Paginator
        archive = record['archive']
        paginator = Paginator(BlogPost.objects.filter(published=True, slug__in=archive['slugs']), archive['per_page'])
        page = paginator.get_page(record.get('page', 1))
        if page.number != record.get('page', 1):
            raise Http404
        return render(request, 'website/blog.html', context(posts=page, archive_title=archive['title']))
    from .models import ContentPage, TeamMember
    from .views import content_page
    slug = request.path.removeprefix('/nl').strip('/')
    page = ContentPage.objects.filter(slug=slug).first() if '/' not in slug else None
    if page:
        if not page.published:
            raise Http404
        return content_page(request, slug)
    member = TeamMember.objects.filter(name__iexact=record.get('heading', '')).first()
    if member:
        if not member.published:
            raise Http404
        return render(request, 'website/team_profile.html', context(member=member))
    paragraphs = list(record.get('paragraphs', []))
    if paragraphs and paragraphs[0] == record.get('heading'):
        paragraphs.pop(0)
    return render(request, 'website/legacy_page.html', context(
        legacy_heading=record.get('heading') or record['title'], legacy_paragraphs=paragraphs))


def legacy_pdf(request, filename):
    path = unquote(request.path)
    record = inventory()['files'].get(path)
    if not record:
        raise Http404
    from .models import ContentPage
    page = ContentPage.objects.filter(slug=record['kind'], published=True).first()
    document = None
    if page:
        document = page.document_nl if record['language'] == 'nl' and page.document_nl else page.document
    if document:
        try:
            return FileResponse(document.open('rb'), content_type='application/pdf')
        except (OSError, ValueError):
            pass
    source = Path(__file__).parent / 'data/legal_documents' / filename
    if not source.is_file():
        raise Http404
    return FileResponse(source.open('rb'), content_type='application/pdf')


def robots_txt(request):
    text = (Path(__file__).parent / 'data/legacy_robots.txt').read_text()
    text = text.replace(_source_inventory()['origin'], inventory()['origin'])
    text = text.replace('Allow: /\n', 'Allow: /\nDisallow: /admin/\nDisallow: /i18n/\nDisallow: /healthz/\n', 1)
    # Do not disallow crawling the preview: Google must see the noindex header.
    return HttpResponse(text, content_type='text/plain; charset=utf-8')


def _published(record, published):
    if record.get('status') != 200 or record.get('redirect') or 'noindex' in record.get('robots', '').lower():
        return False
    kind = record.get('handler')
    if kind in ('post', 'area', 'member'):
        return record['key'] in published[kind]
    if kind == 'page':
        slug = record['internal'].removeprefix('/nl').strip('/')
        if slug not in ('', 'about-us', 'practice-areas', 'blog', 'contact'):
            return slug in published['page']
    if kind == 'legacy':
        slug = urlsplit(record['url']).path.removeprefix('/nl').strip('/')
        if slug in published['existing_pages']:
            return slug in published['page']
        heading = record.get('heading')
        if heading in published['existing_members']:
            return heading in published['member']
    return True


def sitemap(request, filename='sitemap.xml'):
    data = inventory()
    definition = data['sitemaps'].get(filename)
    if not definition:
        raise Http404
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    ET.register_namespace('xhtml', 'http://www.w3.org/1999/xhtml')
    ET.register_namespace('image', 'http://www.google.com/schemas/sitemap-image/1.1')
    if 'children' in definition:
        root = ET.Element('sitemapindex', xmlns=namespace)
        for child in definition['children']:
            node = ET.SubElement(root, 'sitemap')
            ET.SubElement(node, 'loc').text = data['origin'] + '/' + child
    else:
        from .models import BlogPost, ContentPage, PracticeArea, TeamMember
        published = {'post': set(BlogPost.objects.filter(published=True).values_list('slug', flat=True)),
                     'area': set(PracticeArea.objects.filter(published=True).values_list('slug', flat=True)),
                     'member': set(TeamMember.objects.filter(published=True).values_list('name', flat=True)),
                     'page': set(ContentPage.objects.filter(published=True).values_list('slug', flat=True)),
                     'existing_pages': set(ContentPage.objects.values_list('slug', flat=True)),
                     'existing_members': set(TeamMember.objects.values_list('name', flat=True))}
        root = ET.Element('urlset', xmlns=namespace)
        emitted = set()
        for item in definition['pages']:
            record = data['pages'].get(item['path'], {})
            if not _published(record, published):
                continue
            location = record.get('canonical') or record['url']
            if location in emitted:
                continue
            emitted.add(location)
            node = ET.SubElement(root, 'url')
            ET.SubElement(node, 'loc').text = location
            if record.get('lastmod'):
                ET.SubElement(node, 'lastmod').text = record['lastmod']
            for alternate in record.get('alternates', []):
                ET.SubElement(node, '{http://www.w3.org/1999/xhtml}link',
                              rel='alternate', hreflang=alternate['hreflang'], href=alternate['href'])
            for raw in item.get('images', []):
                node.append(ET.fromstring(raw))
        if filename.endswith('blog-posts-sitemap.xml'):
            language = 'nl' if filename.startswith('nl_nl-') else 'en'
            for slug in sorted(published['post'] - set(data['model_paths']['posts'])):
                prefix = '/nl' if language == 'nl' else ''
                node = ET.SubElement(root, 'url')
                ET.SubElement(node, 'loc').text = data['origin'] + prefix + '/post/' + slug
    return HttpResponse(ET.tostring(root, encoding='utf-8', xml_declaration=True), content_type='application/xml')
