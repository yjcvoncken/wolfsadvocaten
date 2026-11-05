from django import template
from website.localization import localized, translate

register = template.Library()
register.filter('localized', localized)
register.simple_tag(translate, name='tr')


class ProfileLinksNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        from website.profile_links import link_profile_mentions
        rendered = self.nodelist.render(context)
        url = context.get('john_wolfs_url')
        request = context.get('request')
        if request and request.path == url:
            return rendered
        return link_profile_mentions(rendered, url)


@register.tag
def profile_links(parser, token):
    nodelist = parser.parse(('endprofile_links',))
    parser.delete_first_token()
    return ProfileLinksNode(nodelist)


@register.filter
def link_article_contacts(text, links):
    from website.article_links import link_contact_paragraphs
    return link_contact_paragraphs(text, links)


@register.filter
def language_url(url):
    from django.urls import translate_url
    from django.utils.translation import get_language, get_language_from_path, override
    if not url or not url.startswith('/') or url.startswith('//'):
        return url
    target = get_language()
    with override(get_language_from_path(url) or 'en'):
        return translate_url(url, target)
