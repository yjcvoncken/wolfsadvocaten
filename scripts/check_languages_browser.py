"""Verify both languages, switching, and responsive translated cards."""
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
options.page_load_strategy = 'eager'
driver = webdriver.Chrome(options=options)
output = Path('/tmp/wolfs-languages-verified')
output.mkdir(exist_ok=True)
results = []
try:
    driver.execute_cdp_cmd('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    for width in (1440, 390):
        driver.set_window_size(width, 900)
        for path in ('/', '/nl/', '/nl/about-us/', '/vacancies/', '/nl/vacancies/', '/nl/contact/'):
            driver.get('http://127.0.0.1:8001' + path)
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState === "complete"'))
            driver.execute_async_script('document.fonts.ready.then(()=>requestAnimationFrame(()=>requestAnimationFrame(arguments[0])))')
            info = driver.execute_script('''return {
                path:location.pathname, language:document.documentElement.lang,
                overflow:document.documentElement.scrollWidth > document.documentElement.clientWidth,
                wrappedNames:[...document.querySelectorAll('.team-meta h3')].filter(h=>h.querySelector('a').getBoundingClientRect().width > h.clientWidth+1).map(h=>h.textContent),
                vacancyColumns:document.querySelector('.vacancy-card') ? getComputedStyle(document.querySelector('.vacancy-card')).gridTemplateColumns : null
            }''')
            assert info['language'] == ('nl' if path.startswith('/nl/') else 'en'), info
            assert not info['overflow'], info
            assert not info['wrappedNames'], info
            results.append({'width': width, **info})
            if path in ('/nl/', '/nl/vacancies/'):
                driver.save_screenshot(str(output / f'{path.strip("/").replace("/", "-")}-{width}.png'))
    driver.get('http://127.0.0.1:8001/vacancies/')
    driver.find_element('css selector', '.language-pill button[value="nl"]').click()
    WebDriverWait(driver, 10).until(lambda d: d.execute_script('return location.pathname === "/nl/vacancies/"'))
    assert driver.find_element('css selector', '.vacancy-card h3').text == 'Advocaat-medewerker'
    driver.find_element('css selector', '.language-pill button[value="en"]').click()
    WebDriverWait(driver, 10).until(lambda d: d.execute_script('return location.pathname === "/vacancies/"'))
    assert driver.find_element('css selector', '.vacancy-card h3').text == 'Associate attorney'
    errors = [e for e in driver.get_log('browser') if e['level'] == 'SEVERE' and 'favicon.ico' not in e['message']]
    assert not errors, errors
    (output / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
finally:
    driver.quit()
