from uuid import uuid4

from django.contrib import admin
from .models import ContentBlock, AboutSection, BlogPost, ContactSubmission, ContentPage, PracticeArea, PracticeAreaSection, SiteSettings, TeamMember, ImportantNetwork, Vacancy

admin.site.site_header = 'Wolfs Advocaten'
admin.site.site_title = 'Wolfs Advocaten admin'
admin.site.index_title = 'Website content'

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [('Brand & introduction', {'fields': ('name','tagline','intro','hero_image','about_image')}), ('Contact details', {'fields': ('phone','email','address','visiting_address','linkedin_url')})]
    def has_add_permission(self, request): return not SiteSettings.objects.exists()

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    exclude = ('show_on_home',)
    list_display = ('name','role','email','order','show_on_about','published')
    list_editable = ('order','show_on_about','published')
    search_fields = ('name','role')
    list_filter = ('published',)

class PracticeAreaSectionInline(admin.StackedInline):
    model = PracticeAreaSection
    extra = 0


@admin.register(PracticeArea)
class PracticeAreaAdmin(admin.ModelAdmin):
    inlines = [PracticeAreaSectionInline]
    list_display = ('title','order','published')
    list_editable = ('order','published')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title','published_at','published')
    list_editable = ('published',)
    list_filter = ('published','published_at')
    search_fields = ('title','excerpt','body')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'

class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 0


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    inlines = [ContentBlockInline]
    list_display = ('title','slug','published')
    list_editable = ('published',)
    prepopulated_fields = {'slug': ('title',)}

@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('first_name','last_name','email','created_at','is_read')
    list_editable = ('is_read',)
    readonly_fields = ('first_name','last_name','email','phone','message','created_at')
    search_fields = ('first_name','last_name','email','message')
    def has_add_permission(self, request): return False


@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'order', 'published')
    list_editable = ('order', 'published')
    list_filter = ('kind', 'published')
    search_fields = ('title', 'lead', 'body')
    fieldsets = [('Content', {'fields': ('title', 'lead', 'body', 'image', 'link')}),
                 ('Placement', {'fields': ('key', 'kind', 'order', 'published')})]


@admin.register(ImportantNetwork)
class ImportantNetworkAdmin(admin.ModelAdmin):
    list_display = ('title', 'link', 'order', 'published')
    list_editable = ('order', 'published')
    list_filter = ('published',)
    search_fields = ('title', 'body', 'link')
    fields = ('title', 'body', 'link', 'order', 'published')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(kind=AboutSection.Kind.NETWORK)

    def save_model(self, request, obj, form, change):
        obj.kind = AboutSection.Kind.NETWORK
        if not obj.key:
            obj.key = f'network-{uuid4().hex}'
        super().save_model(request, obj, form, change)


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'published')
    list_editable = ('order', 'published')
    list_filter = ('published',)
    search_fields = ('title', 'body')
    fields = ('title', 'body', 'link', 'order', 'published')
    actions = ('publish', 'unpublish')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(page__slug='vacancies')

    def save_model(self, request, obj, form, change):
        obj.page, _ = ContentPage.objects.get_or_create(
            slug='vacancies', defaults={'title': 'Vacancies', 'body': ''})
        super().save_model(request, obj, form, change)

    @admin.action(description='Publish selected vacancies', permissions=['change'])
    def publish(self, request, queryset):
        count = queryset.update(published=True)
        self.message_user(request, f'{count} vacancies published.')

    @admin.action(description='Unpublish selected vacancies', permissions=['change'])
    def unpublish(self, request, queryset):
        count = queryset.update(published=False)
        self.message_user(request, f'{count} vacancies unpublished.')

# All public text uses the same English/Dutch editor, including proxy admin sections.
from .translation_forms import expand_fields, translation_form

for content_model in (SiteSettings, TeamMember, PracticeArea, BlogPost, ContentPage,
                      AboutSection, ImportantNetwork, Vacancy):
    editor = admin.site._registry[content_model]
    editor.form = translation_form(content_model)
    editor.exclude = (*tuple(editor.exclude or ()), 'translations')
    if editor.fields:
        editor.fields = expand_fields(editor.fields, content_model)
    if editor.fieldsets:
        editor.fieldsets = [(title, {**options, 'fields': expand_fields(options['fields'], content_model)})
                            for title, options in editor.fieldsets]

ContentBlockInline.form = translation_form(ContentBlock)
ContentBlockInline.exclude = ('translations',)
PracticeAreaSectionInline.form = translation_form(PracticeAreaSection)
PracticeAreaSectionInline.exclude = ('translations',)

from . import photo_admin  # Register the shared Photos gallery.
