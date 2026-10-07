"""Exercise gallery filtering, drag/drop, crop positioning and saving a temporary draft photo."""
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from website.models import TeamMember

user = get_user_model().objects.filter(is_superuser=True, is_active=True).first()
assert user, 'An existing superuser is required for this local browser check.'
client = Client()
client.force_login(user)
session_key = client.cookies['sessionid'].value
member = TeamMember.objects.create(name=f'Photo browser check {uuid4().hex[:8]}', role='Test', published=False)
files = []
driver = None
output = Path('/tmp/wolfs-photos-verified')
output.mkdir(exist_ok=True)
try:
    original = BytesIO()
    Image.new('RGB', (200, 300), 'gray').save(original, 'PNG')
    member.photo.save(f'photo-browser-{uuid4().hex}.png', ContentFile(original.getvalue()))
    files.append(member.photo.name)
    replacement = Image.new('RGB', (800, 300), 'red')
    replacement.paste('blue', (400, 0, 800, 300))
    replacement_path = output / 'replacement.png'
    replacement.save(replacement_path)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1440,1000')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    driver = webdriver.Chrome(options=options)
    driver.get('http://127.0.0.1:8001/admin/login/')
    driver.add_cookie({'name': 'sessionid', 'value': session_key, 'path': '/', 'httpOnly': True})
    driver.get('http://127.0.0.1:8001/admin/website/sitephoto/')
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: d.find_elements('css selector', '.photo-card'))
    total = len(driver.find_elements('css selector', '.photo-card'))
    assert total > 100, total
    driver.save_screenshot(str(output / 'gallery-desktop.png'))
    driver.find_element('id', 'photo-search').send_keys(member.name)
    card = driver.find_element('id', f'photo-teammember-{member.pk}-photo')
    assert card.is_displayed()
    assert driver.find_element('id', 'photo-count').text == '1 photo slots'
    file_input = card.find_element('css selector', '.photo-file')
    file_input.send_keys(str(replacement_path))
    wait.until(lambda d: card.find_element('css selector', '.photo-status').text.startswith('Ready'))
    # Deliver the chosen file through an actual drop event as well.
    driver.execute_script('''const card=arguments[0], transfer=new DataTransfer();
        transfer.items.add(card.querySelector('input[type=file]').files[0]);
        card.querySelector('.photo-dropzone').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));''', card)
    wait.until(lambda d: card.find_element('css selector', '.photo-status').text.startswith('Ready'))
    frame = card.find_element('css selector', '.photo-dropzone')
    ActionChains(driver).move_to_element(frame).click_and_hold().move_by_offset(50, 0).release().perform()
    assert float(card.find_element('css selector', 'input[name=center_x]').get_attribute('value')) < .5
    driver.save_screenshot(str(output / 'crop-preview.png'))
    card.find_element('css selector', 'button[type=submit]').click()
    wait.until(lambda d: card.find_element('css selector', '.photo-status').text.startswith('Saved.'))
    member.refresh_from_db()
    files.append(member.photo.name)
    with Image.open(member.photo.path) as picture:
        assert picture.size == (200, 300), picture.size
    assert not card.find_element('css selector', '.photo-dropzone').get_attribute('class').endswith('is-pending')
    driver.set_window_size(390, 900)
    assert not driver.execute_script('return document.documentElement.scrollWidth > document.documentElement.clientWidth')
    driver.save_screenshot(str(output / 'gallery-mobile.png'))
    errors = [e for e in driver.get_log('browser') if e['level'] == 'SEVERE' and 'favicon.ico' not in e['message']]
    assert not errors, errors
    print(json.dumps({'photos': total, 'drop': 'passed', 'crop': 'passed', 'save': 'passed', 'mobile': 'passed'}))
finally:
    if driver:
        driver.quit()
    member.refresh_from_db()
    if member.photo.name and member.photo.name not in files:
        files.append(member.photo.name)
    member.delete()
    for filename in files:
        default_storage.delete(filename)
    Session.objects.filter(session_key=session_key).delete()
