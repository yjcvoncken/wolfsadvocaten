"""Link profile mentions in rendered page text while preserving existing markup."""
import re
from html.parser import HTMLParser

from django.utils.html import format_html
from django.utils.safestring import mark_safe


class ProfileLinkParser(HTMLParser):
    skipped_tags = {'a', 'button', 'script', 'style', 'textarea', 'svg', 'code', 'pre'}

    def __init__(self, url):
        super().__init__(convert_charrefs=False)
        self.url = url
        self.parts = []
        self.skipped = []

    def handle_starttag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())
        if tag in self.skipped_tags:
            self.skipped.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')
        if self.skipped and self.skipped[-1] == tag:
            self.skipped.pop()

    def handle_data(self, data):
        if not self.skipped:
            data = re.sub(r'\bJohn\s+Wolfs\b', lambda match: str(format_html(
                '<a class="profile-mention" href="{}">{}</a>', self.url, match.group())), data)
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_comment(self, data):
        self.parts.append(f'<!--{data}-->')


def link_profile_mentions(rendered_html, url):
    if not url:
        return rendered_html
    parser = ProfileLinkParser(url)
    parser.feed(str(rendered_html))
    parser.close()
    # Input is already rendered template HTML; only escaped, generated anchors are added.
    return mark_safe(''.join(parser.parts))
