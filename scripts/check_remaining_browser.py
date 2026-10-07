"""Check recorded interior pages at desktop/tablet/mobile sizes."""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--window-size=1440,900')
options.page_load_strategy = 'eager'
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=options)
out = Path('/tmp/remaining-verified')
out.mkdir(exist_ok=True)
results = []
try:
    for width in (1440, 960, 390):
        driver.set_window_size(width, 900)
        for page in ('practice-areas', 'blog', 'social-involvement', 'vacancies', 'contact'):
            driver.get('http://127.0.0.1:8000/' + page + '/')
            time.sleep(.6)
            driver.execute_script("document.documentElement.style.scrollBehavior='auto'")
            height = driver.execute_script('return document.documentElement.scrollHeight')
            for y in range(0, height, 500):
                driver.execute_script('window.scrollTo(0,arguments[0])', y)
                time.sleep(.12)
            time.sleep(.3)
            result = driver.execute_script('''return {
              overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth,
              missing:[...document.querySelectorAll('main img')].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src),
              pending:document.querySelectorAll('.enter-pending').length,
              height:document.documentElement.scrollHeight
            }''')
            result.update(page=page, width=width)
            assert not result['overflow'], result
            assert not result['missing'], result
            assert not result['pending'], result
            driver.execute_script('window.scrollTo(0,0)')
            time.sleep(.2)
            driver.save_screenshot(str(out / f'{page}-{width}.png'))
            results.append(result)
            if page == 'social-involvement' and width == 1440:
                y = driver.execute_script("return document.querySelector('.social-card').getBoundingClientRect().top+scrollY")
                driver.execute_script('window.scrollTo(0,arguments[0])', y)
                time.sleep(.1)
                top = driver.execute_script("return document.querySelector('.social-card').getBoundingClientRect().top")
                assert abs(top - 144) < 1, top
    driver.get('http://127.0.0.1:8000/blog/?page=2')
    assert len(driver.find_elements('css selector', '.reference-post')) == 6
    driver.find_element('css selector', '.menu-pill').click()
    assert driver.find_element('css selector', '#site-menu').is_displayed()
    social = driver.find_element('css selector', '#site-menu a[href="/social-involvement/"]')
    social.click()
    assert driver.current_url.endswith('/social-involvement/')
    driver.get('http://127.0.0.1:8000/advocaat-medewerker/')
    assert 'Advocaat-medewerker' in driver.title
    driver.execute_cdp_cmd('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    driver.get('http://127.0.0.1:8000/contact/')
    assert driver.execute_script("return document.querySelectorAll('.enter-pending').length") == 0
    errors = [entry for entry in driver.get_log('browser') if entry['level'] == 'SEVERE' and 'favicon.ico' not in entry['message']]
    assert not errors, errors
    (out / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
finally:
    driver.quit()
