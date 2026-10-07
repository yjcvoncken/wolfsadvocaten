"""Build a reviewed translation seed from the downloaded original Dutch content."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from bs4 import BeautifulSoup
from website.models import SiteSettings, TeamMember, PracticeArea, BlogPost, ContentPage, AboutSection, ContentBlock
from website.localization import translate, CONTENT_FIELDS
from django.utils.translation import override

ROOT = Path('/tmp/wolfs-dutch-reference')
records = []

def blocks(path):
    soup = BeautifulSoup((ROOT / (path + '.html')).read_text(), 'html.parser')
    return [text(node) for node in soup.select('main .wixui-rich-text')]

def text(node):
    paragraphs = node.find_all(['p', 'h2', 'h3', 'li'])
    return '\n\n'.join(p.get_text(' ', strip=True) for p in paragraphs if p.get_text(' ', strip=True).strip('\u200b')) if paragraphs else node.get_text(' ', strip=True)

def seed(obj, lookup, nl, en=None):
    fields = CONTENT_FIELDS[obj._meta.model_name]
    source = {name: hashlib.sha256(getattr(obj, name).encode()).hexdigest() for name in fields}
    records.append({'model': obj._meta.model_name, 'lookup': lookup, 'source': source, 'nl': nl, 'en': en or {}})

for site in SiteSettings.objects.all():
    seed(site, {'pk': site.pk}, {'tagline': 'Recht. Voor alle ondernemers.', 'intro': 'Proactief, realistisch, internationaal en snel.',
         'address': site.address.replace('The Netherlands', 'Nederland'), 'visiting_address': site.visiting_address.replace('The Netherlands', 'Nederland')})
profiles = {'John Wolfs': 'john-wolfs', 'Maurice van Efferink': 'maurice-vanefferink', 'Joost van den Akker': 'joost-vanden-akker',
            'Menno van Term': 'menno-vanterm', 'Vera Ubaghs': 'vera-ubaghs', 'Ron Meulmeester': 'ron-meulmeester', 'Bas Janssen': 'bas-janssen', 'Gino di Antonio': 'gino-diantonio'}
for member in TeamMember.objects.all():
    with override('nl'): role = translate(member.role)
    nl = {'role': role, 'biography': ''}
    if member.biography:
        if member.name in profiles:
            nl['biography'] = max(blocks(profiles[member.name]), key=len).replace('bijna 25 jaar', 'bijna 30 jaar')
        elif member.name.casefold() == 'yannick voncken':
            nl['biography'] = 'Yannick doet iets'
        else:
            raise ValueError(f'Biography requires translation: {member.name}')
    seed(member, {'name': member.name}, nl)
areas = {'International trade': ('international-trade', 'Internationaal handelsrecht'),
         'Transport & logistics': ('transport', 'Transport en logistiek'), 'Customs law': ('customs', 'Douanerecht'),
         'Commercial advice & litigation': ('commercial-advice-and-litigation', 'Commercieel advies en procedures'),
         'Corporate advice & litigation': ('corporate-advice-and-litigation', 'Ondernemingsrechtelijk advies en procedures'),
         'Liability law and insurance law': ('insurance', 'Aansprakelijkheids- en verzekeringsrecht'),
         'Cannabis law': ('cannabis', 'Cannabisrecht')}
for area in PracticeArea.objects.all():
    path, title = areas[area.title]
    paragraphs = [s for s in blocks(path) if len(s) > 100]
    # The second substantial block is the overview used in the original cards.
    summary = paragraphs[1].split('\n\n')[0]
    seed(area, {'slug': area.slug}, {'title': title, 'summary': summary, 'body': '\n\n'.join(paragraphs)})

normalize = lambda s: re.sub(r'\s+', ' ', s).strip().casefold()
english = {normalize(p['title']): p for p in json.loads((ROOT / 'english-posts.json').read_text())}
dutch = {p.get('translationId'): p for p in json.loads((ROOT / 'posts.json').read_text())}
for post in BlogPost.objects.all():
    reference = dutch[english[normalize(post.title)].get('translationId')]
    soup = BeautifulSoup((ROOT / ('post__' + reference['slug'] + '.html')).read_text(), 'html.parser')
    content = soup.select_one('[data-hook="post-description"]')
    if post.body and not content:
        raise ValueError(f'Article content missing: {post.title}')
    seed(post, {'slug': post.slug}, {'title': reference['title'].strip(), 'excerpt': reference['excerpt'].strip(), 'body': text(content) if content else ''})

about = blocks('about-us')
for section in AboutSection.objects.all():
    if section.key == 'introduction':
        nl = {'title': about[0], 'lead': about[1], 'body': about[2]}
    elif section.key == 'founder':
        nl = {'title': 'John Wolfs', 'lead': 'Advocaat / Oprichter', 'body': about[3]}
    elif section.key == 'since-2003':
        nl = {'title': 'Sinds 2003', 'body': next(s for s in about if s.startswith('Het kantoor is'))}
    else:
        titles = {'experts': 'Experts en teamplayers', 'relationships': 'Langdurige relaties', 'cooperation': 'Samenwerking',
                  'ir-global': 'IR Global', 'incba': 'INCBA', 'aliant': 'Aliant', 'venlo': 'Venlo Freight Village'}
        if section.key not in titles:
            raise ValueError(f'About section requires translation: {section.key}')
        title = titles[section.key]
        index = next(i for i, s in enumerate(about) if normalize(s) == normalize(title))
        body = about[index+1]
        body = '\n\n'.join(p for p in body.split('\n\n') if 'www.irglobal.com' not in p and 'www.venlofreightvillage.nl' not in p)
        nl = {'title': title, 'body': body}
    seed(section, {'key': section.key}, nl)

social = blocks('social-involvement')
for block in ContentBlock.objects.all():
    if block.page.slug == 'vacancies':
        seed(block, {'pk': block.pk}, {'title': block.title, 'body': block.body},
             {'title': 'Associate attorney', 'body': 'Would you like to handle domestic and cross-border cases, and does this vacancy appeal to you?'})
    else:
        title_index = 1 if 'Business Friends' in block.title else 4
        seed(block, {'pk': block.pk}, {'title': social[title_index], 'body': social[title_index+1]})

vacancy_english = '''Wolfs Advocaten is a specialist firm focused on international trade, transport and logistics. Transport and customs law are important areas that we work with every day. Knowledge of commercial and liability law is part of our core expertise. As we serve the sector as a whole, knowledge of insurance, corporate and employment law can also be valuable. English proficiency is required; knowledge of German is an advantage. We preferably expect a commercially minded associate attorney to have knowledge of transport, insurance and/or customs law.

Proactivity, a willingness to learn, empathy and sociability are our core values. You are commercially minded and, above all, a pleasant person to work with.

Where will you work? Our main office is in Maastricht, and we also have an office in Amsterdam. We are looking for candidates who will work primarily from Maastricht. You do not have to be in the office every day: the situation arising from the Covid-19 pandemic has shown that working from home can work well. Team spirit matters to us, however, and requires regular physical presence at the office. Living in Maastricht is not essential.

What will you do? You will meet clients, independently draft advice and court documents, support negotiations and attend hearings when needed. Nevertheless, we apply a four-eyes review policy wherever possible. You will also write blog posts, share knowledge internally and externally, and contribute to our regular case-law lunch.

Business development is important, indeed essential, for an associate attorney. Regular attendance at national and international conferences, participation in business clubs, and attending conferences of networks such as IR Global, of which we are an active member, are therefore a must.

Interested? If this appeals to you, email your CV to info@wolfsadvocaten.nl for the attention of John Wolfs. The confidential application process will consist of two interviews, a case study and/or an assessment.

If you have questions before formally applying, you can contact John Wolfs confidentially at j.wolfs@wolfsadvocaten.nl or 085-0799750.'''
for page in ContentPage.objects.all():
    en = {}
    if page.slug == 'vacancies':
        nl = {'title': 'Met ons samenwerken?', 'lead': 'We zijn altijd op zoek naar nieuw talent. Spreek je (ook) Nederlands, kijk dan eens bij onze vacatures.', 'body': ''}
    elif page.slug == 'social-involvement':
        nl = {'title': social[-3], 'lead': social[-2], 'body': social[-1]}
    elif page.slug == 'advocaat-medewerker':
        nl = {'title': page.title, 'body': page.body, 'lead': page.lead}
        en = {'title': 'Associate attorney', 'body': vacancy_english}
    elif page.slug == 'disclaimer':
        nl = {'title': 'Disclaimer', 'body': blocks('terms-conditions')[0]}
    elif page.slug == 'cookie-policy':
        nl = {'title': 'Cookiebeleid', 'body': blocks('cookie-policy')[0]}
    elif page.slug == 'terms-and-conditions':
        nl = {'title': 'Algemene voorwaarden', 'body': 'Bekijk onze algemene voorwaarden in het downloadbare document.'}
    elif page.slug == 'privacy-statement':
        nl = {'title': 'Privacyverklaring', 'body': 'Bekijk onze privacyverklaring in het downloadbare document.'}
    else:
        raise ValueError(f'Page requires translation: {page.slug}')
    seed(page, {'slug': page.slug}, nl, en)
Path('website/data/translations.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
print(f'Prepared {len(records)} bilingual content records.')
