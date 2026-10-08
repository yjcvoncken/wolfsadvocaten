# Wolfs Advocaten Django site

A Django reproduction of the public Wolfs Advocaten site, with editable team members, articles, practice areas, contact details, and policy pages.

## Deploy on Railway

1. Create a Railway project using **Deploy from GitHub repo** and select `yjcvoncken/wolfsadvocaten`.
2. Attach a **Volume** to the website service and set its mount path to **`/data`**. This keeps uploaded photos and documents across redeploys.
3. Recommended: add a **PostgreSQL** service and set the website service's `DATABASE_URL` to `${{Postgres.DATABASE_URL}}` (use your database service's name). Without PostgreSQL, the app uses SQLite on the attached volume; keep one app replica.
4. In the website service's **Variables**, set:

   | Variable | Value |
   | --- | --- |
   | `DJANGO_SECRET_KEY` | A long random secret, stored only in Railway |
   | `DJANGO_SUPERUSER_USERNAME` | Your chosen admin username |
   | `DJANGO_SUPERUSER_EMAIL` | Your email |
   | `DJANGO_SUPERUSER_PASSWORD` | A strong password, stored only in Railway |

   Generate a secret locally with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. The Docker image already sets `DJANGO_DEBUG=0`. Remove `DJANGO_SUPERUSER_PASSWORD` after the administrator is created; later deployments do not reset an existing administrator's password.
5. In **Settings → Deploy**, set the healthcheck path to `/healthz/` and the timeout to 120 seconds. The Dockerfile supplies the start command automatically.
6. Deploy, then open **Settings → Networking → Generate Domain**. The app accepts the generated Railway domain automatically. Open that domain to view the site and append `/admin/` to edit it.

Railway detects the `Dockerfile`, which configures the build and production Gunicorn server. Configure the readiness check in the dashboard as described above; this project does not depend on Railway's deprecated `railway.json` format. Startup applies migrations, copies initial public media to the volume, and loads the public content snapshot only into an empty website database. Later deployments preserve content edits and replacement photos. No local administrator accounts, passwords, contact submissions or database files are included in the repository.

For a custom domain, set `DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com` and `DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com` in Railway. Keep the volume attached even when using PostgreSQL: the database stores content; the volume stores photos and documents.

Railway setup references: [Django deployment](https://docs.railway.com/guides/django), [persistent volumes](https://docs.railway.com/volumes).

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_site
.venv/bin/python manage.py seed_translations
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Visit http://127.0.0.1:8000/ and sign in at http://127.0.0.1:8000/admin/.

The seed command is safe to rerun; it does not overwrite existing records. Uploaded media is stored in `media/`. The included media files reproduce publicly displayed site images. The blog archive contains 114 posts with article text and images. Contact messages are stored in the admin; no email delivery is configured. The terms and privacy pages link to copies of the original public PDFs. The language selector switches between the local English site (`/`) and Dutch site (`/nl/`), preserving the current page. Navigation, forms, pages, the complete blog archive and legal documents are available in both languages.

For deployment, follow the Railway instructions above. Local development continues to use SQLite and `media/`.

## About us editing

Open `/admin/website/aboutsection/` to edit the introduction, story panels, network descriptions, founder biography and images. Sections have publication and ordering controls. Home, Team and About us share the same published team members and cards. The About us page is at `/about-us/`. Run `seed_about` to add the reference sections to an existing installation without overwriting edits.

The reference measurements and recording informed `about.css`: desktop cards use native sticky positioning, with one-time text entrances. Narrow screens use a single column, and the system’s reduced-motion preference disables entrance animations.

## Remaining recorded pages

Practice areas, Blog, Social involvement, Vacancies and Contact use the shared `remaining.css` layout and `remaining.js` entrance animations. Blog pagination shows six articles per page. Social cards and the Contact office panels use native sticky positioning on desktop.

Edit Social involvement and page introductions under **Content pages** in Django admin. Manage individual vacancies under **Vacancies**, with add, edit, delete, publish and unpublish controls. Manage network entries under **Important networks**. Their photographs, introductions and ordered content blocks are editable there. Published blocks appear on the page; unpublished ones remain hidden. `seed_remaining` adds the included reference content and linked vacancy without overwriting existing records. It also runs as part of `seed_site` for a new installation.

Developer browser checks are in `scripts/check_remaining_browser.py` (requires Selenium and Chrome). They inspect all five pages at 1440, 960 and 390 pixels, check image loading, overflow, navigation, pagination and reduced-motion behavior. Screenshots and results are written under `/tmp/remaining-verified/`.

## English and Dutch content

Public content editors include English fields and Dutch translation fields. Names, contact information, ordering and publication are shared across languages. Edit both language fields when changing a page, article, network, vacancy or team function. A blank Dutch field falls back to the original text.

After upgrading an existing installation, run `migrate` and `seed_translations`. The translation seed preserves existing Dutch translations and checks the original text before filling missing translations, so it skips content edited since the translation snapshot. The Dutch terms and privacy PDFs can be replaced separately using **Document (Dutch)** in Content pages.

`scripts/check_languages_browser.py` verifies language switching, translated desktop/mobile layouts and team name fitting. It expects a local server on port 8001 and writes screenshots to `/tmp/wolfs-languages-verified/`.

## Photo manager

Open **Photos** in admin (`/admin/website/sitephoto/`) to find images by name or section, including team members, blog posts, page images and fixed homepage/contact images. Drop a replacement into the preview or choose a file, drag the preview to adjust its crop (arrow keys also work), and click **Save photo**. The server crops it to the existing photo’s proportions; public page layouts keep their existing frames. Replacements are shared between English and Dutch. Access follows the existing change permissions for each content item.

`scripts/check_photo_manager_browser.py` tests the gallery with an existing local superuser and a temporary unpublished team member. It removes the test member, uploaded test images and temporary login session afterward. It expects a server on port 8001 and writes screenshots to `/tmp/wolfs-photos-verified/`.

## Updating the deployment snapshot

For a fresh installation to start with the current local public content, run `python manage.py export_public_site` and commit `website/data/deployment_content.json` and `website/data/initial_media/`. The export includes only published content and its referenced photos/documents. It excludes users, sessions, contact submissions and drafts. Existing Railway installations keep their own content; changing the snapshot does not overwrite them.

GitHub Actions runs the Django checks and test suite on pushes and pull requests. `scripts/check_production.py` tests fresh production startup, public media and static files using an isolated temporary database and upload directory.
