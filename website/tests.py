from datetime import date
from django.test import TestCase
from django.urls import reverse
from .models import AboutSection, TeamMember, BlogPost, ContactSubmission, PracticeArea

class WebsiteTests(TestCase):
    def test_vacancy_detail_uses_same_footer_layout_and_language_as_listing(self):
        import re
        from django.utils.translation import activate, get_language
        from .models import ContentPage, ContentBlock
        self.addCleanup(activate, get_language())
        listing = ContentPage.objects.create(slug='vacancies', title='Vacancies')
        detail = ContentPage.objects.create(slug='new-attorney', title='New attorney', body='Apply today')
        ContentBlock.objects.create(page=listing, title=detail.title, link='/new-attorney/')
        for language, prefix, label in (('en', '', 'About us'), ('nl', '/nl', 'Over ons')):
            activate(language)
            overview = self.client.get(prefix + '/vacancies/')
            response = self.client.get(prefix + '/new-attorney/')
            self.assertTemplateUsed(response, 'website/vacancy_detail.html')
            for page in (overview, response):
                self.assertContains(page, 'reference-page')
                self.assertContains(page, 'website/remaining.css')
                self.assertContains(page, label)
            footer = lambda page: re.search(r'<footer.*?</footer>', page.content.decode(), re.S).group()
            self.assertEqual(footer(overview), footer(response))

    def test_john_wolfs_mentions_link_across_public_content(self):
        from django.utils.translation import activate, get_language
        from .models import ContentPage, ContentBlock
        self.addCleanup(activate, get_language())
        activate('en')
        john = TeamMember.objects.create(name='John Wolfs', role='Attorney', biography='John Wolfs biography')
        page = ContentPage.objects.create(slug='social-involvement', title='Social involvement',
                                         body='John Wolfs supports these projects.')
        ContentBlock.objects.create(page=page, title='Project', body='Organized by John Wolfs.')
        response = self.client.get(page.get_absolute_url())
        self.assertContains(response, f'<a class="profile-mention" href="{john.get_absolute_url()}">John Wolfs</a>', count=2)
        response = self.client.get('/nl' + page.get_absolute_url())
        self.assertContains(response, 'class="profile-mention" href="/nl/john-wolfs/"', count=2)
        response = self.client.get('/john-wolfs/')
        self.assertNotContains(response, 'class="profile-mention"')

    def test_profile_links_preserve_existing_links_attributes_and_escaping(self):
        from .profile_links import link_profile_mentions
        html = ('<p>John Wolfs &amp; colleagues. &lt;script&gt;</p>'
                '<a href="/john-wolfs/">John Wolfs</a>'
                '<img alt="John Wolfs" src="/portrait.jpg">'
                '<script>const name = "John Wolfs";</script>'
                '<p>John Wolfsburg</p><!-- John Wolfs -->')
        linked = str(link_profile_mentions(html, '/john-wolfs/'))
        self.assertEqual(linked.count('class="profile-mention"'), 1)
        self.assertIn('<a href="/john-wolfs/">John Wolfs</a>', linked)
        self.assertIn('<img alt="John Wolfs" src="/portrait.jpg">', linked)
        self.assertIn('&amp; colleagues. &lt;script&gt;', linked)
        self.assertIn('<script>const name = "John Wolfs";</script>', linked)
        self.assertEqual(link_profile_mentions(html, ''), html)

    def test_optional_employee_line_in_admin_cards_and_profile(self):
        from django.utils.translation import override
        from .translation_forms import translation_form
        from django.forms import modelform_factory
        member = TeamMember.objects.create(name='Example Attorney', role='Attorney')
        self.assertNotContains(self.client.get(reverse('team')), 'team-extra-line')
        form = modelform_factory(TeamMember, form=translation_form(TeamMember), fields='__all__')(data={
            'name': member.name, 'role': 'Attorney', 'extra_line': 'Cooperation partner',
            'extra_line_nl': 'Samenwerkingspartner', 'order': 0, 'published': True, 'show_on_about': True,
        }, instance=member)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertContains(self.client.get(reverse('team')), 'Cooperation partner')
        self.assertContains(self.client.get(member.get_absolute_url()), 'Cooperation partner')
        with override('nl'):
            self.assertContains(self.client.get(reverse('team')), 'Samenwerkingspartner')

    def test_practice_sections_aliases_and_seed_preserve_edits(self):
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings_override = override_settings(MEDIA_ROOT=media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        import json
        from pathlib import Path
        from django.core.management import call_command
        from io import StringIO
        from .models import PracticeAreaSection
        source = next(row for row in json.loads((Path(__file__).parent / 'data/profiles.json').read_text())
                      if row[:2] == ['area', 'Customs law'])
        area = PracticeArea.objects.create(title='Customs law', slug='customs-law', body=source[2])
        call_command('seed_practice_details', stdout=StringIO())
        self.assertEqual(area.sections.count(), 3)
        member = TeamMember.objects.create(name='John Wolfs', role='Attorney')
        for url in (area.get_absolute_url(), reverse('content_page', args=['customs'])):
            response = self.client.get(url)
            self.assertContains(response, '<h2>Import duties (classification)</h2>', html=True)
            self.assertContains(response, 'practice-detail-primary')
            self.assertContains(response, 'practice-detail-secondary')
            self.assertContains(response, member.get_absolute_url())
        section = area.sections.first()
        section.body = 'Admin edited topic'
        section.save()
        call_command('seed_practice_details', stdout=StringIO())
        section.refresh_from_db()
        self.assertEqual(section.body, 'Admin edited topic')
        customized = PracticeArea.objects.create(title='Cannabis law', slug='cannabis-law', body='Custom legal text')
        call_command('seed_practice_details', stdout=StringIO())
        self.assertFalse(PracticeAreaSection.objects.filter(area=customized).exists())
        self.assertContains(self.client.get(customized.get_absolute_url()), 'Custom legal text')

    def test_article_contact_links_are_localized_and_escape_text(self):
        from django.utils.translation import activate, get_language
        self.addCleanup(activate, get_language())
        activate('en')
        member = TeamMember.objects.create(name='John Wolfs')
        area = PracticeArea.objects.create(title='Customs law', slug='customs-law',
                                          translations={'nl': {'title': 'Douanerecht'}})
        post = BlogPost.objects.create(
            title='Contact links', published_at=date.today(), published=True,
            body='Customs law overview.\n\nFeel free to contact attorney John Wolfs about customs law. <script>alert(1)</script>',
            translations={'nl': {'body': 'Neem contact op met John Wolfs over douanerecht.'}},
        )
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, f'class="article-inline-link" href="{member.get_absolute_url()}">John Wolfs</a>')
        self.assertContains(response, f'class="article-inline-link" href="{area.get_absolute_url()}">customs law</a>')
        self.assertContains(response, '<p>Customs law overview.</p>', html=True)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        response = self.client.get('/nl' + post.get_absolute_url())
        self.assertContains(response, 'href="/nl/john-wolfs/">John Wolfs</a>')
        self.assertContains(response, '>douanerecht</a>')
        member.published = False
        member.save()
        self.assertNotContains(self.client.get(post.get_absolute_url()), '>John Wolfs</a>')

    def test_public_routes_and_draft_visibility(self):
        area = PracticeArea.objects.create(title='Transport', slug='transport', summary='Transport advice', published=True)
        post = BlogPost.objects.create(title='Draft article', slug='draft-article', body='Body', published_at=date.today(), published=False)
        for name in ('home', 'about', 'practice_areas', 'blog', 'contact'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(area.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(reverse('original_post', args=[post.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('blog')), post.title)
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)

    def test_contact_form_saves_valid_message(self):
        from django.core import mail
        response = self.client.post(reverse('contact'), {'first_name':'Ada','last_name':'Lovelace','email':'ada@example.com','phone':'','message':'Hello'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.assertContains(response, 'Your message has been received')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['info@wolfsadvocaten.nl'])
        self.assertEqual(mail.outbox[0].reply_to, ['ada@example.com'])
        self.assertIn('Ada Lovelace', mail.outbox[0].body)
        self.assertIn('Hello', mail.outbox[0].body)

    def test_contact_mail_failure_preserves_submission(self):
        from unittest.mock import patch
        from smtplib import SMTPException
        with patch('website.views.mail.mailers') as mailers:
            mailers.__getitem__.return_value.send_messages.side_effect = SMTPException('Unavailable')
            with self.assertLogs('website.views', level='ERROR'):
                response = self.client.post(reverse('contact'), {
                    'first_name': 'Ada', 'last_name': 'Lovelace',
                    'email': 'ada@example.com', 'message': 'Please contact me',
                })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactSubmission.objects.count(), 1)


    def test_about_content_and_team_publication(self):
        section = AboutSection.objects.create(key='experts', title='Edited expertise', body='Admin supplied text', kind='story')
        AboutSection.objects.create(key='hidden', title='Hidden section', published=False)
        member = TeamMember.objects.create(name='About team member', role='Attorney', show_on_home=False)
        TeamMember.objects.create(name='Home only member', role='Attorney', show_on_about=False)
        page = self.client.get(reverse('about'))
        self.assertContains(page, section.title)
        self.assertContains(page, section.body)
        self.assertContains(page, member.name)
        self.assertNotContains(page, 'Home only member')
        self.assertNotContains(page, 'Hidden section')
        self.assertContains(self.client.get(reverse('home')), member.name)

    def test_about_seed_preserves_admin_edits(self):
        from django.core.management import call_command
        from io import StringIO
        call_command('seed_about', stdout=StringIO())
        section = AboutSection.objects.get(key='introduction')
        section.title = 'Our edited introduction'
        section.save()
        call_command('seed_about', stdout=StringIO())
        section.refresh_from_db()
        self.assertEqual(section.title, 'Our edited introduction')
        self.assertEqual(AboutSection.objects.filter(key='introduction').count(), 1)

    def test_remaining_pages_and_published_blocks(self):
        from .models import ContentBlock, ContentPage
        page = ContentPage.objects.create(slug='social-involvement', title='Social involvement', lead='Our involvement')
        ContentBlock.objects.create(page=page, title='Published activity', body='Editable activity text')
        ContentBlock.objects.create(page=page, title='Private activity', published=False)
        response = self.client.get(page.get_absolute_url())
        self.assertContains(response, 'Our involvement')
        self.assertContains(response, 'Published activity')
        self.assertNotContains(response, 'Private activity')

    def test_blog_has_six_posts_per_page(self):
        for number in range(7):
            BlogPost.objects.create(title=f'Article {number}', body='Article body', published_at=date.today(), published=True)
        first = self.client.get(reverse('blog'))
        second = self.client.get(reverse('blog'), {'page': 2})
        self.assertEqual(len(first.context['posts']), 6)
        self.assertEqual(len(second.context['posts']), 1)
        self.assertContains(first, 'aria-label="Next page"')

    def test_contact_invalid_form_keeps_errors(self):
        response = self.client.post(reverse('contact'), {'first_name': 'Ada', 'email': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid email address')
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_legal_documents_open_directly_and_old_routes_redirect(self):
        from .models import ContentPage
        for slug in ('terms-and-conditions', 'privacy-statement'):
            page = ContentPage.objects.create(slug=slug, title=slug, document=f'documents/{slug}.pdf')
            self.assertRedirects(self.client.get(page.get_absolute_url()), page.document.url, fetch_redirect_response=False)
            self.assertContains(self.client.get(reverse('home')), f'href="{page.document.url}" target="_blank" rel="noopener"')
        for slug in ('disclaimer', 'cookie-policy'):
            page = ContentPage.objects.create(slug=slug, title=slug, body='Original legal text')
            response = self.client.get(page.get_absolute_url())
            self.assertContains(response, page.body)
            self.assertTemplateUsed(response, 'website/legal_page.html')
        self.assertContains(self.client.get('/terms-conditions/'), 'Original legal text')

    def test_linkedin_is_available_in_footer_and_menu(self):
        from .models import SiteSettings
        url = 'https://www.linkedin.com/company/wolfs-advocaten/posts/'
        SiteSettings.objects.create(linkedin_url=url)
        response = self.client.get(reverse('contact'))
        self.assertContains(response, f'href="{url}" target="_blank" rel="noopener"', count=2)

    def test_team_changes_are_shared_across_pages(self):
        from .models import SiteSettings
        site = SiteSettings.objects.create(phone='+31 85 123 4567')
        member = TeamMember.objects.create(
            name='Original member', role='Attorney', email='old@example.com',
            photo='team/old.jpg', show_on_home=False, show_on_about=True)
        member.name = 'Updated member'
        member.role = 'Senior attorney'
        member.email = 'updated@example.com'
        member.photo = 'team/updated.jpg'
        member.save()
        routes = ('home', 'team', 'about')
        for route in routes:
            response = self.client.get(reverse(route))
            self.assertContains(response, member.name)
            self.assertContains(response, member.role)
            self.assertContains(response, member.email)
            self.assertContains(response, member.photo.url)
            self.assertContains(response, site.phone)
            self.assertNotContains(response, 'Original member')
            self.assertTemplateUsed(response, 'website/team_card.html')
            self.assertEqual(list(response.context['team']), [member])
        member.published = False
        member.save()
        for route in routes:
            self.assertNotContains(self.client.get(reverse(route)), member.name)

    def test_important_networks_can_be_managed_in_admin(self):
        from django.contrib.auth import get_user_model
        from .models import ImportantNetwork
        self.client.force_login(get_user_model().objects.create_superuser(
            username='network-editor', email='editor@example.com', password='test-password'))
        original = AboutSection.objects.create(
            key='ir-global', kind='network', title='Existing network', body='Original text')
        AboutSection.objects.create(key='other-story', kind='story', title='Other story')
        listing = self.client.get(reverse('admin:website_importantnetwork_changelist'))
        self.assertContains(listing, original.title)
        self.assertNotContains(listing, 'Other story')
        response = self.client.post(
            reverse('admin:website_importantnetwork_change', args=[original.pk]), {
                'title': 'Updated network', 'body': 'Updated description',
                'link': 'https://new-network.example.com/', 'order': 2,
                'published': 'on', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse('about'))
        self.assertContains(page, 'Updated network')
        self.assertContains(page, 'Updated description')
        self.assertContains(page, 'https://new-network.example.com/', count=2)
        self.assertNotContains(page, 'www.irglobal.com')
        response = self.client.post(reverse('admin:website_importantnetwork_add'), {
            'title': 'New network', 'body': 'New description',
            'link': '', 'order': 1, 'published': 'on', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        added = ImportantNetwork.objects.get(title='New network')
        self.assertEqual(added.kind, 'network')
        self.assertTrue(added.key)
        page = self.client.get(reverse('about'))
        self.assertEqual(list(page.context['networks'].values_list('title', flat=True)),
                         ['New network', 'Updated network'])
        added.published = False
        added.save()
        self.assertNotContains(self.client.get(reverse('about')), 'New network')

    def test_vacancies_admin_lifecycle(self):
        from django.contrib.auth import get_user_model
        from .models import ContentBlock, ContentPage, Vacancy
        self.client.force_login(get_user_model().objects.create_superuser(
            username='vacancy-editor', email='jobs@example.com', password='test-password'))
        page = ContentPage.objects.create(slug='vacancies', title='Vacancies', body='Join us')
        existing = ContentBlock.objects.create(page=page, title='Existing opening', body='Description')
        other = ContentPage.objects.create(slug='social-involvement', title='Social involvement')
        ContentBlock.objects.create(page=other, title='Community activity')
        listing = self.client.get(reverse('admin:website_vacancy_changelist'))
        self.assertContains(listing, existing.title)
        self.assertNotContains(listing, 'Community activity')
        response = self.client.post(reverse('admin:website_vacancy_add'), {
            'title': 'New attorney vacancy', 'body': 'Join our legal team',
            'link': '/contact/', 'order': 1, '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        vacancy = Vacancy.objects.get(title='New attorney vacancy')
        self.assertEqual(vacancy.page, page)
        self.assertNotContains(self.client.get('/vacancies/'), vacancy.title)
        for action, visible in (('publish', True), ('unpublish', False), ('publish', True)):
            response = self.client.post(reverse('admin:website_vacancy_changelist'), {
                'action': action, '_selected_action': str(vacancy.pk)})
            self.assertEqual(response.status_code, 302)
            vacancy.refresh_from_db()
            self.assertEqual(vacancy.published, visible)
            public = self.client.get('/vacancies/')
            if visible:
                self.assertContains(public, vacancy.title)
                self.assertContains(public, vacancy.body)
            else:
                self.assertNotContains(public, vacancy.title)
        response = self.client.post(reverse('admin:website_vacancy_delete', args=[vacancy.pk]),
                                    {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Vacancy.objects.filter(pk=vacancy.pk).exists())
        self.assertNotContains(self.client.get('/vacancies/'), vacancy.title)
        existing.published = False
        existing.save()
        self.assertContains(self.client.get('/vacancies/'), 'There are currently no open vacancies.')


class TranslationTests(TestCase):
    def setUp(self):
        from .models import ContentPage, SiteSettings
        SiteSettings.objects.create(tagline='Law for entrepreneurs', translations={
            'nl': {'tagline': 'Recht voor ondernemers', 'intro': 'Praktisch en snel'}})
        self.page = ContentPage.objects.create(slug='vacancies', title='Work with us', translations={
            'nl': {'title': 'Werken bij ons'}})

    def test_both_languages_and_internal_vacancy_links(self):
        from .models import ContentBlock
        ContentBlock.objects.create(page=self.page, title='Associate attorney', body='Join us',
                                   link='/contact/', translations={'nl': {
                                       'title': 'Advocaat-medewerker', 'body': 'Kom bij ons werken'}})
        english = self.client.get('/vacancies/')
        dutch = self.client.get('/nl/vacancies/')
        self.assertContains(english, '<html lang="en">')
        self.assertContains(english, 'Associate attorney')
        self.assertContains(dutch, '<html lang="nl">')
        self.assertContains(dutch, 'Werken bij ons')
        self.assertContains(dutch, 'Advocaat-medewerker')
        self.assertContains(dutch, 'Locatie:')
        self.assertContains(dutch, 'href="/nl/contact/"')
        self.assertNotContains(dutch, 'https://www.wolfsadvocaten.nl/" lang="nl"')
        self.assertContains(self.client.get('/nl/'), 'Recht voor ondernemers')
        self.assertContains(self.client.get('/'), 'Law for entrepreneurs')

    def test_language_switch_preserves_page_and_query_in_both_directions(self):
        response = self.client.post('/i18n/setlang/', {'language': 'nl', 'next': '/blog/?page=2'})
        self.assertEqual(response.url, '/nl/blog/?page=2')
        self.assertEqual(response.cookies['django_language'].value, 'nl')
        response = self.client.post('/i18n/setlang/', {'language': 'en', 'next': '/nl/blog/?page=2'})
        self.assertEqual(response.url, '/blog/?page=2')
        self.assertEqual(response.cookies['django_language'].value, 'en')
        response = self.client.post('/i18n/setlang/', {'language': 'nl', 'next': 'https://other.example.com/'})
        self.assertEqual(response.url, '/nl/')

    def test_contact_labels_validation_and_confirmation_in_dutch(self):
        response = self.client.get('/nl/contact/')
        self.assertContains(response, 'Voornaam')
        self.assertContains(response, 'Achternaam')
        self.assertContains(response, 'VERZENDEN')
        response = self.client.post('/nl/contact/', {'email': 'invalid'})
        self.assertContains(response, 'Voer een geldig e-mailadres in.')
        response = self.client.post('/nl/contact/', {
            'first_name': 'Jan', 'last_name': 'Jansen', 'email': 'jan@example.com',
            'phone': '', 'message': 'Hallo'}, follow=True)
        self.assertContains(response, 'Bedankt. Uw bericht is ontvangen.')

    def test_dutch_legal_documents(self):
        from .models import ContentPage
        page = ContentPage.objects.create(slug='terms-and-conditions', title='Terms',
                                         document='documents/en.pdf', document_nl='documents/nl.pdf')
        self.assertRedirects(self.client.get('/terms-and-conditions/'), page.document.url, fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/nl/terms-and-conditions/'), page.document_nl.url, fetch_redirect_response=False)
        self.assertContains(self.client.get('/nl/'), f'href="{page.document_nl.url}"')

    def test_admin_edit_dutch_vacancy_and_preserve_translation_on_bulk_publish(self):
        from django.contrib.auth import get_user_model
        from .models import Vacancy
        self.client.force_login(get_user_model().objects.create_superuser(
            username='translator', email='translator@example.com', password='test-password'))
        response = self.client.get(reverse('admin:website_vacancy_add'))
        self.assertContains(response, 'Title (English)')
        self.assertContains(response, 'Title (Dutch)')
        response = self.client.post(reverse('admin:website_vacancy_add'), {
            'title': 'New role', 'body': 'English description', 'title_nl': 'Nieuwe functie',
            'body_nl': 'Nederlandse beschrijving', 'link': '/contact/', 'order': 1, '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        vacancy = Vacancy.objects.get(title='New role')
        self.client.post(reverse('admin:website_vacancy_changelist'), {
            'action': 'publish', '_selected_action': str(vacancy.pk)})
        vacancy.refresh_from_db()
        self.assertEqual(vacancy.translations['nl']['title'], 'Nieuwe functie')
        self.assertContains(self.client.get('/nl/vacancies/'), 'Nieuwe functie')
        self.assertContains(self.client.get('/vacancies/'), 'New role')

    def test_all_public_templates_render_in_dutch(self):
        from .models import BlogPost, ContentPage, PracticeArea
        area = PracticeArea.objects.create(title='International trade', summary='Advice',
                                          translations={'nl': {'title': 'Internationaal handelsrecht', 'summary': 'Advies'}})
        post = BlogPost.objects.create(title='News', body='Article', published=True, published_at=date.today(),
                                      translations={'nl': {'title': 'Nieuws', 'body': 'Artikel'}})
        member = TeamMember.objects.create(name='John Example', role='Attorney')
        for slug in ('social-involvement', 'disclaimer', 'cookie-policy'):
            ContentPage.objects.create(slug=slug, title=slug)
        paths = ('/', '/about-us/', '/team/', '/practice-areas/', '/blog/', '/contact/', '/vacancies/',
                 '/social-involvement/', '/disclaimer/', '/cookie-policy/', area.get_absolute_url(),
                 post.get_absolute_url(), member.get_absolute_url())
        for path in paths:
            response = self.client.get('/nl' + path)
            self.assertEqual(response.status_code, 200, path)
            self.assertContains(response, '<html lang="nl">')
        self.assertContains(self.client.get(f'/nl/blog/{post.slug}/'), 'Artikel')
        self.assertContains(self.client.get(f'/nl/practice-areas/{area.slug}/'), 'Internationaal handelsrecht')

    def test_translation_seed_preserves_admin_edits_and_is_repeatable(self):
        from django.core.management import call_command
        from io import StringIO
        section = AboutSection.objects.create(
            key='experts', kind='story', title='Edited expertise', body='Edited English body',
            translations={'nl': {'title': 'Eigen Nederlandse kop'}})
        for _ in range(2):
            call_command('seed_translations', stdout=StringIO())
            section.refresh_from_db()
            self.assertEqual(section.title, 'Edited expertise')
            self.assertEqual(section.body, 'Edited English body')
            self.assertEqual(section.translations['nl']['title'], 'Eigen Nederlandse kop')
            self.assertNotIn('body', section.translations['nl'])

    def test_page_seed_does_not_duplicate_translated_vacancies(self):
        from django.core.management import call_command
        from io import StringIO
        from .models import ContentBlock
        ContentBlock.objects.create(page=self.page, title='Associate attorney',
                                   translations={'nl': {'title': 'Advocaat-medewerker'}})
        call_command('seed_remaining', stdout=StringIO())
        self.assertEqual(self.page.blocks.count(), 1)
