from .seo import original_path
from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image
from .models import BlogPost, SitePhoto, TeamMember


def image_file(name='replacement.png', size=(800, 300)):
    picture = Image.new('RGB', size, 'red')
    picture.paste('blue', (size[0] // 2, 0, size[0], size[1]))
    output = BytesIO()
    picture.save(output, 'PNG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')


class PhotoManagerTests(TestCase):
    def setUp(self):
        self.storage = TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.override = self.settings(MEDIA_ROOT=self.storage.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_superuser(
            username='photo-editor', email='photo@example.com', password='test-password')
        self.client.force_login(self.user)
        self.member = TeamMember.objects.create(name='Photo member', role='Attorney',
            translations={'nl': {'role': 'Advocaat'}})
        self.member.photo.save('original.png', ContentFile(image_file(size=(200, 300)).read()), save=True)
        self.url = reverse('admin:website_photo_replace', args=('teammember', self.member.pk, 'photo'))
        self.gallery = reverse('admin:website_sitephoto_changelist')

    def test_gallery_and_photo_replacement_are_shared_across_pages(self):
        page = self.client.get(self.gallery)
        self.assertContains(page, self.member.name)
        self.assertContains(page, 'Home — how we work')
        self.assertContains(page, 'photo-dropzone')
        original_name = self.member.photo.name
        response = self.client.post(self.url, {'photo': image_file()}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['width'], response.json()['height']), (200, 300))
        self.member.refresh_from_db()
        self.assertNotEqual(self.member.photo.name, original_name)
        self.assertEqual(self.member.translations['nl']['role'], 'Advocaat')
        self.assertEqual(self.member.role, 'Attorney')
        for path in ('/', '/team/', '/about-us/', '/nl/', '/nl/team/', '/nl/about-us/'):
            self.assertContains(self.client.get(original_path(path)), self.member.photo.url)

    def test_crop_position_is_applied_on_server(self):
        for center, color in ((0, (255, 0, 0)), (1, (0, 0, 255))):
            response = self.client.post(self.url, {'photo': image_file(), 'center_x': center, 'center_y': .5},
                                        HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)
            self.member.refresh_from_db()
            with Image.open(self.member.photo.path) as picture:
                self.assertEqual(picture.size, (200, 300))
                pixel = picture.getpixel((100, 150))
                self.assertTrue(all(abs(a - b) < 3 for a, b in zip(pixel, color)), pixel)

    def test_invalid_image_or_crop_does_not_change_the_photo(self):
        original = self.member.photo.name
        invalid = SimpleUploadedFile('photo.jpg', b'not an image', content_type='image/jpeg')
        for data in ({'photo': invalid}, {'photo': image_file(), 'center_x': 2},
                     {'photo': image_file(), 'center_x': 'nan'}):
            response = self.client.post(self.url, data, HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 400)
            self.member.refresh_from_db()
            self.assertEqual(self.member.photo.name, original)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.client.post(reverse('admin:website_photo_replace',
            args=('teammember', self.member.pk, 'name')), {'photo': image_file()}).status_code, 404)

    def test_permissions_are_checked_for_each_photo(self):
        from datetime import date
        post = BlogPost.objects.create(title='Restricted article', body='Body', published_at=date.today())
        staff = get_user_model().objects.create_user(username='team-only', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename='change_teammember'))
        self.client.force_login(staff)
        page = self.client.get(self.gallery)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, self.member.name)
        self.assertNotContains(page, post.title)
        self.assertNotContains(page, 'Home — how we work')
        target = reverse('admin:website_photo_replace', args=('blogpost', post.pk, 'image'))
        self.assertEqual(self.client.post(target, {'photo': image_file()}).status_code, 403)
        self.assertEqual(self.client.post(self.url, {'photo': image_file()}, HTTP_ACCEPT='application/json').status_code, 200)
        staff.user_permissions.clear()
        self.assertEqual(self.client.get(self.gallery).status_code, 403)

    def test_fixed_homepage_photo_is_editable_in_both_languages(self):
        slot = SitePhoto.objects.get(key='method_photo')
        target = reverse('admin:website_photo_replace', args=('sitephoto', slot.pk, 'image'))
        self.assertEqual(self.client.post(target, {'photo': image_file()}, HTTP_ACCEPT='application/json').status_code, 200)
        slot.refresh_from_db()
        for path in ('/', '/nl/'):
            self.assertContains(self.client.get(original_path(path)), slot.image.url)
        contact = SitePhoto.objects.get(key='contact_office')
        target = reverse('admin:website_photo_replace', args=('sitephoto', contact.pk, 'image'))
        self.client.post(target, {'photo': image_file()}, HTTP_ACCEPT='application/json')
        contact.refresh_from_db()
        self.assertContains(self.client.get('/contact'), contact.image.url)

    def test_upload_requires_csrf_token(self):
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        self.assertEqual(protected.post(self.url, {'photo': image_file()}).status_code, 403)
