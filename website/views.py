from django.contrib import messages
from django.core import mail
import logging
from smtplib import SMTPException
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
    john = TeamMember.objects.filter(name__iexact='John Wolfs', published=True).first()
    legal = {page.slug: page for page in ContentPage.objects.filter(
        slug__in=('terms-and-conditions', 'privacy-statement'), published=True)}
    def document_link(slug):
        from .seo import inventory
        language = 'nl' if (get_language() or '').startswith('nl') else 'en'
        for path, record in inventory()['files'].items():
            if record['kind'] == slug and record['language'] == language:
                return path
        page = legal.get(slug)
        document = page.document_nl if page and (get_language() or '').startswith('nl') and page.document_nl else (page.document if page else None)
        return document.url if document else reverse('content_page', args=[slug])
    return {'site': settings(), 'site_photos': fixed_photo_urls(), 'john_wolfs_url': john.get_absolute_url() if john else '', 'terms_document_url': document_link('terms-and-conditions'),
            'privacy_document_url': document_link('privacy-statement'), **kwargs}

def home(request):
    return render(request, 'website/home.html', context(areas=PracticeArea.objects.filter(published=True), team=TeamMember.objects.filter(published=True), posts=BlogPost.objects.filter(published=True)[:6]))

def about(request):
    from django.templatetags.static import static
    team = list(TeamMember.objects.filter(published=True, show_on_about=True))
    original_order = {name: index for index, name in enumerate((
        'John Wolfs', 'Maurice van Efferink', 'Joost van den Akker', 'Menno van Term',
        'Ella Delanty', 'Romy Brüll', 'Vera Ubaghs',
    ))}
    team.sort(key=lambda member: original_order.get(member.name, len(original_order)))
    original_portraits = {
        'John Wolfs': ('website/images/about-team/john.png', {
            'team/john.jpg', 'team/john-wolfs-reference-20261021.jpg',
        }),
        'Joost van den Akker': ('website/images/about-team/joost.png', {
            'team/joost.jpg', 'team/joost-van-den-akker-reference-20261021.png',
            'team/joost-van-den-akker-current-20261105.jpg',
        }),
    }
    for member in team:
        portrait = original_portraits.get(member.name)
        if portrait and member.photo.name in portrait[1]:
            member.team_card_photo_url = static(portrait[0])
    sections = AboutSection.objects.filter(published=True)
    return render(request, 'website/about.html', context(
        intro=sections.filter(kind='intro').first(),
        stories=sections.filter(kind='story'),
        networks=sections.filter(kind='network'),
        founder=sections.filter(kind='founder').first(),
        founder_member=TeamMember.objects.filter(name='John Wolfs', published=True).first(),
        team=team,
    ))

def practice_areas(request):
    return render(request, 'website/practice_areas.html', context(areas=PracticeArea.objects.filter(published=True)))

def practice_detail(request, slug):
    area = get_object_or_404(PracticeArea, slug=slug, published=True)
    sections = list(area.sections.all())
    return render(request, 'website/practice_detail.html', context(
        area=area,
        intro_sections=[section for section in sections if section.position == 'intro'],
        detail_sections=[section for section in sections if section.position == 'detail'],
        contact_member=TeamMember.objects.filter(name__iexact='John Wolfs', published=True).first(),
    ))

def blog(request):
    number = getattr(request, 'legacy_seo', None) or {}
    posts = Paginator(BlogPost.objects.filter(published=True), 6).get_page(number.get('page') or request.GET.get('page'))
    if number.get('page') and posts.number != number['page']:
        raise Http404
    return render(request, 'website/blog.html', context(posts=posts))

def blog_detail(request, slug):
    from .article_links import contact_links
    return render(request, 'website/blog_detail.html', context(
        post=get_object_or_404(BlogPost, slug=slug, published=True),
        article_links=contact_links(TeamMember.objects.filter(published=True),
                                    PracticeArea.objects.filter(published=True)),
    ))

def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        submission = form.save()
        notification = mail.EmailMessage(
            subject='Nieuw bericht via het contactformulier — Wolfs Advocaten',
            body=(f'Naam: {submission.first_name} {submission.last_name}\n'
                  f'E-mail: {submission.email}\nTelefoon: {submission.phone}\n\n'
                  f'Bericht:\n{submission.message}'),
            to=['info@wolfsadvocaten.nl'],
            reply_to=[submission.email],
        )
        try:
            if mail.mailers['default'].send_messages([notification]) != 1:
                raise SMTPException('Contact notification was not accepted by the mail server')
        except (SMTPException, OSError):
            logging.getLogger(__name__).exception(
                'Could not email contact submission %s; retained in admin', submission.pk)
        messages.success(request, translate('Thank you. Your message has been received.'))
        from .seo import original_path
        return redirect(original_path(reverse('contact')))
    return render(request, 'website/contact.html', context(form=form))

def content_page(request, slug):
    if slug == 'terms-conditions':
        slug = 'disclaimer'
    area_aliases = {'international-trade':'International trade','transport':'Transport & logistics','customs':'Customs law','commercial-advice-and-litigation':'Commercial advice & litigation','corporate-advice-and-litigation':'Corporate advice & litigation','insurance':'Liability law and insurance law','cannabis':'Cannabis law'}
    if slug in area_aliases:
        area = get_object_or_404(PracticeArea, title=area_aliases[slug], published=True)
        return practice_detail(request, area.slug)
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
    elif slug == 'advocaat-medewerker' or ContentPage.objects.filter(
        slug='vacancies', published=True, blocks__published=True,
        blocks__link__in=(f'/{slug}/', f'/{slug}', f'/nl/{slug}/', f'/nl/{slug}'),
    ).exists():
        template = 'website/vacancy_detail.html'
    else:
        template = 'website/landing_page.html' if slug in ('social-involvement', 'vacancies') else 'website/content_page.html'
    return render(request, template, context(page=page, blocks=page.blocks.filter(published=True)))


def switch_language(request):
    from urllib.parse import urlsplit
    from django.conf import settings as django_settings
    from django.utils.translation import get_language_from_path, override
    from django.views.i18n import set_language
    next_url = request.POST.get('next', request.GET.get('next', '/'))
    from .seo import translated_path
    language = request.POST.get('language')
    if request.method == 'POST' and language in dict(django_settings.LANGUAGES):
        request.POST = request.POST.copy()
        request.POST['next'] = translated_path(next_url, language)
        next_url = request.POST['next']
    source_language = get_language_from_path(urlsplit(next_url).path) or django_settings.LANGUAGE_CODE
    with override(source_language):
        response = set_language(request)
    if response.has_header('Location'):
        from .seo import original_path
        response['Location'] = original_path(response['Location'])
    return response
