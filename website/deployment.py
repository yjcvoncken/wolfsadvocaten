"""Production health and uploaded-file endpoints."""
import mimetypes
from pathlib import Path
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.db import connection, DatabaseError
from django.http import FileResponse, Http404, JsonResponse
from django.utils._os import safe_join
from django.views.decorators.http import require_safe


@require_safe
def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except DatabaseError:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


@require_safe
def public_media(request, path):
    try:
        filename = Path(safe_join(settings.MEDIA_ROOT, path))
    except SuspiciousFileOperation:
        raise Http404
    if not filename.is_file():
        raise Http404
    # Resolve symlinks too: media files must stay inside the public upload directory.
    if not filename.resolve().is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
        raise Http404
    content_type = mimetypes.guess_type(filename.name)[0] or 'application/octet-stream'
    inline = content_type in ('image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif', 'application/pdf')
    try:
        response = FileResponse(filename.open('rb'), content_type=content_type, as_attachment=not inline)
    except OSError:
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'public, max-age=3600'
    return response
