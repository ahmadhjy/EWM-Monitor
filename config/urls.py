from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

from content import views
from content.feeds import LatestArticlesFeed
from content.sitemaps import ArticleSitemap, CategorySitemap, PageSitemap, StaticSitemap


sitemaps = {
    "articles": ArticleSitemap,
    "categories": CategorySitemap,
    "pages": PageSitemap,
    "static": StaticSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tinymce/", include("tinymce.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("llms.txt", views.llms_txt, name="llms_txt"),
    path("health/", views.health, name="health"),
]

urlpatterns += i18n_patterns(
    path("feed/", LatestArticlesFeed(), name="feed"),
    path("", include("content.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "content.views.error_404"
handler500 = "content.views.error_500"
