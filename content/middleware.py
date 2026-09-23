from django.utils import translation
from django.conf import settings


class EnglishAdminMiddleware:
    """Keep the editorial UI English regardless of public language or cookies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(("/admin/", "/tinymce/")):
            with translation.override("en"):
                request.LANGUAGE_CODE = "en"
                return self.get_response(request)
        return self.get_response(request)


class IndexingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.SITE_INDEXING_ENABLED:
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
