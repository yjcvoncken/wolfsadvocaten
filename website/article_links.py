"""Render plain article text with internal links in contact paragraphs."""
import re

from django.utils.html import format_html, format_html_join
from django.utils.text import normalize_newlines

from .localization import localized


def contact_links(team, areas):
    links = {}
    for member in team:
        links[member.name.casefold()] = member.get_absolute_url()
    for area in areas:
        for title in (area.title, localized(area, 'title')):
            if title:
                links[title.casefold()] = area.get_absolute_url()
    return links


def link_contact_paragraphs(text, links):
    if not links:
        return format_html('{}', text)
    pattern = re.compile(r'(?<!\w)(' + '|'.join(
        re.escape(label) for label in sorted(links, key=len, reverse=True)
    ) + r')(?!\w)', re.IGNORECASE)
    parts = []
    for paragraph in re.split(r'(\n\s*\n)', normalize_newlines(text)):
        if not re.search(r'\bcontact\b', paragraph, re.IGNORECASE):
            parts.append(format_html('{}', paragraph))
            continue
        offset = 0
        for match in pattern.finditer(paragraph):
            parts.append(format_html('{}', paragraph[offset:match.start()]))
            parts.append(format_html('<a class="article-inline-link" href="{}">{}</a>',
                                     links[match.group().casefold()], match.group()))
            offset = match.end()
        parts.append(format_html('{}', paragraph[offset:]))
    return format_html_join('', '{}', ((part,) for part in parts))
