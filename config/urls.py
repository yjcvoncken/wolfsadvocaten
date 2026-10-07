from django.contrib import admin
from django.urls import path
from django.conf.urls.i18n import i18n_patterns
from website import views
from website.deployment import healthz, public_media

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('media/<path:path>', public_media, name='public_media'),
    path('admin/', admin.site.urls),
    path('i18n/setlang/', views.switch_language, name='set_language'),
]

urlpatterns += i18n_patterns(
    path('', views.home, name='home'),
    path('about-us/', views.about, name='about'),
    path('team/', views.about, name='team'),
    path('practice-areas/', views.practice_areas, name='practice_areas'),
    path('practice-areas/<slug:slug>/', views.practice_detail, name='practice_detail'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('post/<slug:slug>/', views.blog_detail, name='original_post'),
    path('contact/', views.contact, name='contact'),
    path('<slug:slug>/', views.content_page, name='content_page'),
    prefix_default_language=False,
)
