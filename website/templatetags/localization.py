from django import template
from website.localization import localized, translate

register = template.Library()
register.filter('localized', localized)
register.simple_tag(translate, name='tr')


@register.filter
def language_url(url):
    from django.urls import translate_url
    from django.utils.translation import get_language, get_language_from_path, override
    if not url or not url.startswith('/') or url.startswith('//'):
        return url
    target = get_language()
    with override(get_language_from_path(url) or 'en'):
        return translate_url(url, target)
