from datetime import date
from django.test import TestCase
from django.urls import reverse
from .models import AboutSection, TeamMember, BlogPost, ContactSubmission, PracticeArea

class WebsiteTests(TestCase):
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
        response = self.client.post(reverse('contact'), {'first_name':'Ada','last_name':'Lovelace','email':'ada@example.com','phone':'','message':'Hello'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.assertContains(response, 'Your message has been received')


    def test_about_content_and_team_publication(self):
        section = AboutSection.objects.create(key='experts', title='Edited expertise', body='Admin supplied text', kind='story')
        AboutSection.objects.create(key='hidden', title='Hidden section', published=False)
        member = TeamMember.objects.create(name='About team member', role='Attorney', show_on_home=False)
        TeamMember.objects.create(name='Home only member', role='Attorney', show_on_about=False)
        page = self.client.get(reverse('about'))
        self.assertContains(page, section.title)
        self.assertContains(page, section.body)
        self.assertContains(page, member.name)
        self.assertContains(page, 'Home only member')
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
            photo='team/old.jpg', show_on_home=False, show_on_about=False)
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
