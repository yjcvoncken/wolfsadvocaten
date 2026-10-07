from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.utils.translation import get_language
from django.urls import reverse
from .localization import translate
from .photo_manager import fixed_photo_urls
from .forms import ContactForm
from .models import AboutSection, BlogPost, ContentPage, PracticeArea, SiteSettings, TeamMember


def settings(): return SiteSettings.objects.first() or SiteSettings()
def context(**kwargs):
    legal = {page.slug: page for page in ContentPage.objects.filter(
        slug__in=('terms-and-conditions', 'privacy-statement'), published=True)}
    def document_link(slug):
        page = legal.get(slug)
        document = page.document_nl if page and (get_language() or '').startswith('nl') and page.document_nl else (page.document if page else None)
        return document.url if document else reverse('content_page', args=[slug])
    return {'site': settings(), 'site_photos': fixed_photo_urls(), 'terms_document_url': document_link('terms-and-conditions'),
            'privacy_document_url': document_link('privacy-statement'), **kwargs}

def home(request):
    return render(request, 'website/home.html', context(areas=PracticeArea.objects.filter(published=True), team=TeamMember.objects.filter(published=True), posts=BlogPost.objects.filter(published=True)[:6]))

def about(request):
    sections = AboutSection.objects.filter(published=True)
    return render(request, 'website/about.html', context(
        intro=sections.filter(kind='intro').first(),
        stories=sections.filter(kind='story'),
        networks=sections.filter(kind='network'),
        founder=sections.filter(kind='founder').first(),
        founder_member=TeamMember.objects.filter(name='John Wolfs', published=True).first(),
        team=TeamMember.objects.filter(published=True),
    ))

def practice_areas(request):
    return render(request, 'website/practice_areas.html', context(areas=PracticeArea.objects.filter(published=True)))

def practice_detail(request, slug):
    return render(request, 'website/practice_detail.html', context(area=get_object_or_404(PracticeArea, slug=slug, published=True)))

def blog(request):
    posts = Paginator(BlogPost.objects.filter(published=True), 6).get_page(request.GET.get('page'))
    return render(request, 'website/blog.html', context(posts=posts))

def blog_detail(request, slug):
    return render(request, 'website/blog_detail.html', context(post=get_object_or_404(BlogPost, slug=slug, published=True)))

def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, translate('Thank you. Your message has been received.'))
        return redirect('contact')
    return render(request, 'website/contact.html', context(form=form))

def content_page(request, slug):
    if slug == 'terms-conditions':
        slug = 'disclaimer'
    area_aliases = {'international-trade':'International trade','transport':'Transport & logistics','customs':'Customs law','commercial-advice-and-litigation':'Commercial advice & litigation','corporate-advice-and-litigation':'Corporate advice & litigation','insurance':'Liability law and insurance law','cannabis':'Cannabis law'}
    if slug in area_aliases:
        area = get_object_or_404(PracticeArea, title=area_aliases[slug], published=True)
        return render(request, 'website/practice_detail.html', context(area=area))
    aliases = {'maurice-vanefferink':'Maurice van Efferink','joost-vanden-akker':'Joost van den Akker','menno-vanterm':'Menno van Term','gino-diantonio':'Gino di Antonio'}
    member = next((m for m in TeamMember.objects.filter(published=True) if slugify(m.name) == slug or m.name == aliases.get(slug)), None)
    if member:
        return render(request, 'website/team_profile.html', context(member=member))
    page = get_object_or_404(ContentPage, slug=slug, published=True)
    if slug in ('terms-and-conditions', 'privacy-statement') and page.document:
        document = page.document_nl if (get_language() or '').startswith('nl') and page.document_nl else page.document
        return redirect(document.url)
    if slug in ('disclaimer', 'cookie-policy'):
        template = 'website/legal_page.html'
    else:
        template = 'website/landing_page.html' if slug in ('social-involvement', 'vacancies') else 'website/content_page.html'
    return render(request, template, context(page=page, blocks=page.blocks.filter(published=True)))


def switch_language(request):
    from urllib.parse import urlsplit
    from django.conf import settings as django_settings
    from django.utils.translation import get_language_from_path, override
    from django.views.i18n import set_language
    next_url = request.POST.get('next', request.GET.get('next', '/'))
    source_language = get_language_from_path(urlsplit(next_url).path) or django_settings.LANGUAGE_CODE
    with override(source_language):
        return set_language(request)
