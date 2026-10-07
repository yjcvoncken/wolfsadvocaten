"""Shared image slots, gallery metadata, and server-side replacement cropping."""
from io import BytesIO
from math import isfinite
from pathlib import Path
from uuid import uuid4
from django import forms
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.templatetags.static import static
from PIL import Image, ImageOps
from .models import AboutSection, BlogPost, ContentBlock, ContentPage, PracticeArea, SitePhoto, SiteSettings, TeamMember

FIXED_PHOTOS = {
    'hero_slide_2': ('Home — hero slide 2', 'website/images/hero-2.jpg', 'static'),
    'hero_slide_3': ('Home — hero slide 3', 'website/images/hero-3.jpg', 'static'),
    'practice_banner': ('Home — practice areas banner', 'website/images/practice-banner.jpg', 'static'),
    'method_photo': ('Home — how we work', 'website/images/method.jpg', 'static'),
    'contact_office': ('Contact — office photo', 'site/contact.jpg', 'media'),
}
PHOTO_MODELS = {
    'sitesettings': (SiteSettings, ('hero_image', 'about_image'), 'Home'),
    'sitephoto': (SitePhoto, ('image',), 'Site photos'),
    'teammember': (TeamMember, ('photo',), 'Team'),
    'practicearea': (PracticeArea, ('image',), 'Practice areas'),
    'aboutsection': (AboutSection, ('image',), 'About us'),
    'contentpage': (ContentPage, ('image',), 'Pages'),
    'contentblock': (ContentBlock, ('image',), 'Page sections'),
    'blogpost': (BlogPost, ('image',), 'Blog'),
}
DEFAULT_SIZES = {'teammember': (800, 1000), 'practicearea': (900, 1200), 'blogpost': (1200, 800)}


def fixed_photo_urls():
    replacements = {photo.key: photo.image.url for photo in SitePhoto.objects.exclude(image='')}
    return {key: replacements.get(key) or (static(path) if kind == 'static' else settings.MEDIA_URL + path)
            for key, (_, path, kind) in FIXED_PHOTOS.items()}


def image_details(obj, field):
    image = getattr(obj, field)
    url = image.url if image else ''
    dimensions = DEFAULT_SIZES.get(obj._meta.model_name, (1200, 800))
    try:
        if image:
            with image.open('rb') as source, Image.open(source) as picture:
                dimensions = ImageOps.exif_transpose(picture).size
        elif isinstance(obj, SitePhoto):
            _, path, kind = FIXED_PHOTOS[obj.key]
            url = static(path) if kind == 'static' else settings.MEDIA_URL + path
            source = finders.find(path) if kind == 'static' else Path(settings.MEDIA_ROOT) / path
            with Image.open(source) as picture:
                dimensions = ImageOps.exif_transpose(picture).size
    except (OSError, ValueError, KeyError):
        pass
    width, height = dimensions
    scale = min(1, 2400 / max(width, height))
    return url, (max(1, round(width * scale)), max(1, round(height * scale)))


class PhotoReplacementForm(forms.Form):
    photo = forms.ImageField()
    center_x = forms.FloatField(min_value=0, max_value=1, initial=.5, required=False)
    center_y = forms.FloatField(min_value=0, max_value=1, initial=.5, required=False)

    def clean(self):
        cleaned = super().clean()
        for field in ('center_x', 'center_y'):
            value = cleaned.get(field)
            if value is not None and not isfinite(value):
                self.add_error(field, 'Choose a valid crop position.')
        return cleaned


def replace_photo(obj, field, form):
    _, dimensions = image_details(obj, field)
    upload = form.cleaned_data['photo']
    upload.seek(0)
    with Image.open(upload) as original:
        original = ImageOps.exif_transpose(original)
        center = tuple(.5 if form.cleaned_data.get(name) is None else form.cleaned_data[name]
                       for name in ('center_x', 'center_y'))
        cropped = ImageOps.fit(original, dimensions, method=Image.Resampling.LANCZOS, centering=center)
        transparent = cropped.mode in ('RGBA', 'LA') or 'transparency' in cropped.info
        output = BytesIO()
        if transparent:
            cropped.convert('RGBA').save(output, format='PNG', optimize=True)
            extension = 'png'
        else:
            cropped.convert('RGB').save(output, format='JPEG', quality=90, optimize=True)
            extension = 'jpg'
    image = getattr(obj, field)
    image.save(f'{obj._meta.model_name}-{obj.pk}-{uuid4().hex}.{extension}', ContentFile(output.getvalue()), save=False)
    # Update only this image: simultaneous text edits in admin are preserved.
    obj.save(update_fields=[field])
    return image.url, dimensions
