"""One admin gallery for the image fields used throughout the website."""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.views.decorators.http import require_POST
from .models import ContentBlock, ContentPage, SitePhoto
from .photo_manager import PHOTO_MODELS, PhotoReplacementForm, image_details, replace_photo


@admin.register(SitePhoto)
class PhotoAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return any(request.user.has_perm(f'website.{action}_{name}')
                   for name in PHOTO_MODELS for action in ('view', 'change'))

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def allowed(self, request, obj, change=False):
        if isinstance(obj, SitePhoto):
            method = super().has_change_permission if change else super().has_view_permission
            return method(request, obj)
        target = obj.page if isinstance(obj, ContentBlock) else obj
        editor = self.admin_site._registry.get(type(target))
        if not editor:
            return False
        method = editor.has_change_permission if change else editor.has_view_permission
        return method(request, target)

    def get_urls(self):
        return [
            path('', self.admin_site.admin_view(self.gallery), name='website_sitephoto_changelist'),
            path('replace/<str:model_name>/<int:object_id>/<str:field_name>/',
                 self.admin_site.admin_view(require_POST(self.replace)), name='website_photo_replace'),
        ]

    def gallery(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        photos = []
        for model_name, (model, fields, category) in PHOTO_MODELS.items():
            objects = model.objects.all()
            if model is ContentBlock:
                objects = objects.select_related('page')
            for obj in objects:
                if not self.allowed(request, obj):
                    continue
                for field in fields:
                    url, (width, height) = image_details(obj, field)
                    title = str(obj)
                    if model_name == 'sitesettings':
                        title = 'Home — hero photo' if field == 'hero_image' else 'Home — about us photo'
                    elif isinstance(obj, ContentBlock):
                        title = f'{obj.page.title} — {obj.title}'
                    identifier = f'{model_name}-{obj.pk}-{field}'
                    photos.append({'id': identifier, 'title': title, 'category': category, 'url': url,
                                   'width': width, 'height': height, 'editable': self.allowed(request, obj, True),
                                   'action': reverse('admin:website_photo_replace', args=(model_name, obj.pk, field))})
        return TemplateResponse(request, 'admin/website/photo_gallery.html', {
            **self.admin_site.each_context(request), 'title': 'Photos', 'opts': self.model._meta,
            'photos': photos, 'categories': sorted({photo['category'] for photo in photos}),
        })

    def replace(self, request, model_name, object_id, field_name):
        specification = PHOTO_MODELS.get(model_name)
        if not specification or field_name not in specification[1]:
            raise Http404
        obj = get_object_or_404(specification[0], pk=object_id)
        if not self.allowed(request, obj, True):
            raise PermissionDenied
        form = PhotoReplacementForm(request.POST, request.FILES)
        wants_json = 'application/json' in request.headers.get('Accept', '')
        if form.is_valid():
            url, (width, height) = replace_photo(obj, field_name, form)
            self.log_change(request, obj, [{'changed': {'fields': [obj._meta.get_field(field_name).verbose_name]}}])
            if wants_json:
                return JsonResponse({'url': url, 'width': width, 'height': height, 'message': 'Photo saved.'})
            messages.success(request, 'Photo saved.')
        else:
            errors = [str(error) for values in form.errors.values() for error in values]
            if wants_json:
                return JsonResponse({'errors': errors}, status=400)
            messages.error(request, ' '.join(errors))
        return redirect(reverse('admin:website_sitephoto_changelist') + f'#photo-{model_name}-{object_id}-{field_name}')
