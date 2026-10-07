"""Read the existing public Dutch website into a local translation reference."""
import concurrent.futures
import json
from pathlib import Path
import time
import urllib.request
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path('/tmp/wolfs-dutch-reference')
ROOT.mkdir(exist_ok=True)
BASE = 'https://www.wolfsadvocaten.nl/nl/'

def fetch(path, language='nl'):
    base = BASE if language == 'nl' else 'https://www.wolfsadvocaten.nl/'
    target = ROOT / (('en__' if language == 'en' else '') + path.replace('/', '__') + '.html')
    if target.exists():
        return target.read_text()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(base + quote(path), timeout=30) as response:
                html = response.read().decode('utf-8')
            target.write_text(html)
            return html
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)

def records(value):
    if isinstance(value, str):
        try:
            yield from records(json.loads(value))
        except (ValueError, TypeError):
            pass
    elif isinstance(value, dict):
        if value.get('slug') and value.get('firstPublishedDate') and 'title' in value:
            yield value
        else:
            for item in value.values():
                yield from records(item)
    elif isinstance(value, list):
        for item in value:
            yield from records(item)

def listing(page, language='nl'):
    path = 'blog' if page == 1 else f'blog/page/{page}'
    soup = BeautifulSoup(fetch(path, language), 'html.parser')
    return list(records(json.loads(soup.find(id='wix-warmup-data').get_text())))

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    posts = {post['slug']: post for batch in pool.map(listing, range(1, 20)) for post in batch}
print(f'Found {len(posts)} Dutch article records.', flush=True)
(ROOT / 'posts.json').write_text(json.dumps(list(posts.values()), ensure_ascii=False, indent=2))
paths = ['post/' + slug for slug in posts]
paths += ['about-us', 'international-trade', 'transport', 'customs', 'commercial-advice-and-litigation',
          'corporate-advice-and-litigation', 'insurance', 'cannabis', 'john-wolfs', 'maurice-vanefferink',
          'joost-vanden-akker', 'menno-vanterm', 'vera-ubaghs', 'ron-meulmeester', 'bas-janssen',
          'gino-diantonio', 'vacancies', 'social-involvement', 'terms-conditions', 'cookie-policy',
          'advocaat-medewerker', 'contact', 'practice-areas']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for index, _ in enumerate(pool.map(fetch, paths), 1):
        if index % 20 == 0:
            print(f'Downloaded {index}/{len(paths)} reference pages.', flush=True)
print('Dutch reference download complete.', flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    english = {post['slug']: post for batch in pool.map(lambda page: listing(page, 'en'), range(1, 20)) for post in batch}
(ROOT / 'english-posts.json').write_text(json.dumps(list(english.values()), ensure_ascii=False, indent=2))
print(f'Matched reference index: {len(english)} English articles.', flush=True)
