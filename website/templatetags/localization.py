from django import template
from website.localization import localized, translate

register = template.Library()
register.filter('localized', localized)
register.simple_tag(translate, name='tr')


class OriginalURLNode(template.Node):
    def __init__(self, node):
        self.node = node

    def render(self, context):
        from website.seo import original_path
        result = self.node.render(context)
        if self.node.asvar:
            context[self.node.asvar] = original_path(context[self.node.asvar])
            return result
        if self.node.view_name.resolve(context) == 'team':
            from django.utils.translation import get_language
            return ('/nl' if (get_language() or '').startswith('nl') else '/') + '#anchors-l4qwqckn2'
        return original_path(result)


@register.tag
def original_url(parser, token):
    from django.template.defaulttags import url
    return OriginalURLNode(url(parser, token))


@register.simple_tag(takes_context=True)
def pagination_url(context, number):
    from website.seo import original_path
    path = original_path(context['request'].path)
    if '/page/' in path:
        path = path.rsplit('/page/', 1)[0]
    return path if int(number) == 1 else path + '/page/' + str(number)


@register.simple_tag
def blog_categories():
    from django.utils.translation import get_language
    from website.seo import inventory
    translations = {
        'cannabis-law': 'cannabis-law-2', 'international-trade': 'internationale-handel',
        'transport-logistics': 'transport-logistiek', 'customs-law': 'douanerecht',
        'commercial-advice-litigation': 'commercieel-recht',
        'corporate-advice-litigation': 'ondernemingsrecht',
        'liability-law-and-insurance-law': 'aansprakelijkheids-en-verzekerings',
        'employment-law': 'arbeidsrecht',
    }
    dutch = (get_language() or '').startswith('nl')
    result = []
    for english, translated in translations.items():
        path = ('/nl' if dutch else '') + '/blog/categories/' + (translated if dutch else english)
        result.append({'url': path, 'title': inventory()['pages'][path]['archive']['title']})
    return result


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
    from website.seo import translated_path
    from django.urls import translate_url
    from django.utils.translation import get_language, get_language_from_path, override
    if not url or not url.startswith('/') or url.startswith('//'):
        return url
    target = get_language()
    translated = translated_path(url, target.split('-')[0])
    if translated != url:
        return translated
    with override(get_language_from_path(url) or 'en'):
        return translate_url(url, target)
