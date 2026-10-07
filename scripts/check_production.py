"""Smoke-test production startup without changing the development database or uploads."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

project = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='wolfs-production-') as directory:
    root = Path(directory)
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        port = port_socket.getsockname()[1]
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('DATABASE_URL', 'RAILWAY_VOLUME_MOUNT_PATH') and not key.startswith('DJANGO_SUPERUSER_')}
    environment.update({
        'PATH': str(project / '.venv/bin') + os.pathsep + os.environ['PATH'],
        'DJANGO_DEBUG': '0', 'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
        'DJANGO_SQLITE_PATH': str(root / 'db.sqlite3'), 'DJANGO_MEDIA_ROOT': str(root / 'media'),
        'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1,healthcheck.railway.app', 'PORT': str(port),
        'WEB_CONCURRENCY': '1',
    })
    log = (root / 'server.log').open('w+')
    process = subprocess.Popen(['sh', 'scripts/start.sh'], cwd=project, env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    def request(path, secure=True):
        headers = {'X-Forwarded-Proto': 'https'} if secure else {}
        with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=10) as response:
            return response.status, response.headers, response.read()
    try:
        for _ in range(100):
            if process.poll() is not None:
                log.seek(0)
                raise AssertionError('Production startup failed: ' + log.read()[-3000:])
            try:
                if request('/healthz/', secure=False)[0] == 200:
                    break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(.2)
        else:
            raise AssertionError('Production startup timed out')
        snapshot = json.loads((project / 'website/data/deployment_content.json').read_text())
        hero = next(record['fields']['hero_image'] for record in snapshot if record['model'] == 'website.sitesettings')
        for path in ('/', '/nl/', '/admin/login/', '/vacancies/', '/nl/vacancies/',
                     '/static/website/home.css', '/static/admin/css/base.css', '/media/' + hero):
            status, headers, body = request(path)
            assert status == 200 and body, (path, status)
        status, headers, body = request('/nl/')
        assert b'<html lang="nl">' in body
        assert b'Yannick' in body
        print('Production startup, English/Dutch pages, admin login, static files and uploaded media: passed.')
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()
