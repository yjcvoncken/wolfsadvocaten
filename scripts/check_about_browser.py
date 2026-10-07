"""Browser checks for the reproduced About us page (requires Selenium/Chrome)."""
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
output = Path('/tmp/wolfs-about-verified')
output.mkdir(exist_ok=True)
results = []
try:
    for width in (1440, 960, 390):
        driver.set_window_size(width, 900)
        driver.get('http://127.0.0.1:8000/about-us/')
        time.sleep(2)
        driver.execute_script("document.documentElement.style.scrollBehavior='auto'")
        height = driver.execute_script('return document.documentElement.scrollHeight')
        for y in range(0, height, 500):
            driver.execute_script('window.scrollTo(0,arguments[0])', y)
            time.sleep(.12)
        time.sleep(1.5)
        info = driver.execute_script('''return {
          width:innerWidth, height:document.documentElement.scrollHeight,
          overflow:document.documentElement.scrollWidth > document.documentElement.clientWidth,
          missingImages:[...document.querySelectorAll('img')].filter(i=>getComputedStyle(i).display!=='none'&&(!i.complete||i.naturalWidth===0)).map(i=>i.src),
          teamCards:document.querySelectorAll('.about-team .team-card').length,
          pending:[...document.querySelectorAll('.about-enter-pending')].length
        }''')
        assert not info['overflow'], info
        assert not info['missingImages'], info
        assert info['teamCards'] == 10, info
        assert info['pending'] == 0, info
        driver.execute_script('window.scrollTo(0,0)')
        time.sleep(.2)
        driver.save_screenshot(str(output / f'about-{width}.png'))
        if width == 1440:
            sticky_y = driver.execute_script("return document.querySelector('.story-experts').getBoundingClientRect().top + scrollY + 150")
            driver.execute_script('window.scrollTo(0,arguments[0])', sticky_y)
            time.sleep(.2)
            top = driver.execute_script("return document.querySelector('.story-experts').getBoundingClientRect().top")
            assert abs(top) < 1, top
            driver.save_screenshot(str(output / 'about-sticky.png'))
        results.append(info)
    driver.execute_cdp_cmd('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    driver.get('http://127.0.0.1:8000/about-us/')
    time.sleep(.5)
    assert driver.execute_script("return document.querySelectorAll('.about-enter-pending').length") == 0
    # Verify the earlier homepage changes still render with the shared team roster.
    driver.get('http://127.0.0.1:8000/')
    time.sleep(.5)
    assert driver.execute_script("return document.querySelectorAll('.home-team .team-card').length") == 10
    errors = [entry for entry in driver.get_log('browser') if entry['level'] == 'SEVERE' and 'favicon.ico' not in entry['message']]
    assert not errors, errors
    (output / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
finally:
    driver.quit()
