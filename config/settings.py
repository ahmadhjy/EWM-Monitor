from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "local-development-key-change-before-deploy")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [item.strip() for item in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if item.strip()]
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
SITE_INDEXING_ENABLED = os.getenv("SITE_INDEXING_ENABLED", "True").lower() == "true"
TRUST_PROXY_CLIENT_IP = os.getenv("TRUST_PROXY_CLIENT_IP", "False").lower() == "true"

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "tinymce",
    "content.apps.ContentConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "content.middleware.EnglishAdminMiddleware",
    "content.middleware.IndexingMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "content.context_processors.site_context",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

database_url = os.getenv("DATABASE_URL", "")
if database_url.startswith("postgres"):
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
LANGUAGES = [
    ("ar", "العربية"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Beirut")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/admin/"
APPEND_SLASH = True
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
trusted_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [item.strip() for item in trusted_origins.split(",") if item.strip()]
if not CSRF_TRUSTED_ORIGINS and SITE_URL.startswith("https://"):
    CSRF_TRUSTED_ORIGINS = [SITE_URL]

FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "elliottwavemonitor@gmail.com")
CONTACT_EMAIL_NOTIFICATIONS = os.getenv("CONTACT_EMAIL_NOTIFICATIONS", "False").lower() == "true"

TINYMCE_DEFAULT_CONFIG = {
    "language": "en",
    "directionality": "ltr",
    "height": 620,
    "menubar": "file edit view insert format tools table help",
    "plugins": "advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table help wordcount",
    "toolbar": "undo redo | blocks | bold italic forecolor backcolor | alignleft aligncenter alignright | bullist numlist outdent indent | link image media table blockquote | removeformat code fullscreen help",
    "image_advtab": True,
    "file_picker_types": "image",
    "file_picker_callback": "ewmMediaPicker",
    "relative_urls": False,
    "remove_script_host": True,
    "content_style": "body { font-family: Inter, system-ui, sans-serif; font-size: 17px; line-height: 1.7; max-width: 820px; margin: 24px auto; } img { max-width: 100%; height: auto; }",
}

TINYMCE_EXTRA_MEDIA = {
    "js": ["admin/js/media-library-picker.js"],
    "css": {"all": ["admin/css/media-library-picker.css"]},
}

UNFOLD = {
    "SITE_TITLE": "EWM Editorial",
    "SITE_HEADER": "Elliott Wave Monitor",
    "SITE_SUBHEADER": "Publishing & SEO dashboard",
    "SITE_ICON": "/static/img/ewm-mark.svg",
    "SITE_FAVICONS": [{"rel": "icon", "sizes": "any", "type": "image/svg+xml", "href": "/static/img/ewm-mark.svg"}],
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "content.admin.admin_environment",
    "COLORS": {
        "primary": {
            "50": "#fff9eb",
            "100": "#fff0c7",
            "200": "#fddf8a",
            "300": "#f7ca66",
            "400": "#efb64e",
            "500": "#e6ad45",
            "600": "#c98a28",
            "700": "#9f671d",
            "800": "#7f4f19",
            "900": "#693f17",
            "950": "#3d220a",
        }
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Publishing",
                "separator": True,
                "items": [
                    {"title": "Articles", "icon": "article", "link": "/admin/content/article/"},
                    {"title": "Pages", "icon": "web", "link": "/admin/content/page/"},
                    {"title": "Categories", "icon": "category", "link": "/admin/content/category/"},
                    {"title": "Media", "icon": "image", "link": "/admin/content/mediaasset/"},
                ],
            },
            {
                "title": "Site management",
                "separator": True,
                "items": [
                    {"title": "Site settings", "icon": "settings", "link": "/admin/content/sitesettings/"},
                    {"title": "Navigation", "icon": "menu", "link": "/admin/content/menuitem/"},
                    {"title": "Redirects", "icon": "move_up", "link": "/admin/content/redirect/"},
                    {"title": "Messages", "icon": "mail", "link": "/admin/content/contactmessage/"},
                    {"title": "Newsletter subscribers", "icon": "group", "link": "/admin/content/newslettersubscriber/"},
                ],
            },
        ],
    },
}
