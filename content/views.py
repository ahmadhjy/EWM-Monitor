from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme
import hashlib
import logging
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils import translation
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

from .forms import ContactForm, NewsletterForm
from .i18n import is_arabic, ui_text
from .models import Article, Category, NewsletterSubscriber, Page, Redirect, SiteSettings


def form_rate_limited(request, purpose, limit):
    address = request.META.get("REMOTE_ADDR", "unknown")
    if settings.TRUST_PROXY_CLIENT_IP:
        address = request.META.get("HTTP_X_REAL_IP", address)
    key = f"form:{purpose}:{hashlib.sha256(address.encode()).hexdigest()}"
    if cache.add(key, 1, 600):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        return False


def published_articles():
    queryset = (
        Article.objects.filter(status="published", published_at__lte=timezone.now())
        .select_related("category")
        .prefetch_related("additional_categories")
    )
    if is_arabic():
        queryset = queryset.exclude(title_ar="").exclude(body_ar="")
    return queryset


def page_context(request, obj=None, **extra):
    canonical = settings.SITE_URL + request.path
    if obj and getattr(obj, "canonical_url", "") and not is_arabic():
        canonical = obj.canonical_url
    alternates = {}
    match = request.resolver_match
    if match and match.view_name:
        for code in ("ar", "en"):
            with translation.override(code):
                route = reverse(match.view_name, kwargs=match.kwargs or None, args=match.args or None)
            alternates[code] = settings.SITE_URL + route
    if isinstance(obj, Article) and not obj.has_arabic_translation:
        alternates["ar"] = ""
    return {
        "seo_object": obj,
        "canonical_url": canonical,
        "alternate_ar_url": alternates.get("ar", settings.SITE_URL + "/"),
        "alternate_en_url": alternates.get("en", settings.SITE_URL + "/en/"),
        **extra,
    }


def home(request):
    articles = published_articles()
    featured = articles.filter(is_featured=True).first() or articles.first()
    latest = articles.exclude(pk=featured.pk if featured else None)[:8]
    trending = articles.filter(is_trending=True)[:6]
    categories = Category.objects.filter(is_visible=True).order_by("order", "name")
    return render(
        request,
        "content/home.html",
        page_context(
            request,
            featured=featured,
            latest=latest,
            trending=trending,
            categories=categories,
            article_total=articles.count(),
            page_title=("توقعات موجات إليوت وتحليل الأسواق" if is_arabic() else "Elliott Wave Forecasts & Market Analysis"),
            page_description=SiteSettings.load().display_tagline,
        ),
    )


def article_detail(request, article):
    related = (
        published_articles()
        .filter(category=article.category)
        .exclude(pk=article.pk)[:3]
    )
    return render(
        request,
        "content/article_detail.html",
        page_context(request, article, article=article, related=related),
    )


def category_detail(request, category):
    articles = published_articles().filter(Q(category=category) | Q(additional_categories=category)).distinct()
    return render(
        request,
        "content/category_detail.html",
        page_context(request, category, category=category, articles=articles),
    )


def page_detail(request, page):
    return render(request, "content/page_detail.html", page_context(request, page, page=page))


def content_detail(request, slug):
    article = published_articles().filter(slug=slug).first()
    if article:
        return article_detail(request, article)

    # Hidden categories stay out of navigation but their historical URLs remain valid.
    category = Category.objects.filter(slug=slug).first()
    if category:
        return category_detail(request, category)

    page = Page.objects.filter(slug=slug, status="published").first()
    if page:
        return page_detail(request, page)

    redirect_rule = Redirect.objects.filter(old_path=request.path).first()
    if redirect_rule:
        Redirect.objects.filter(pk=redirect_rule.pk).update(hits=redirect_rule.hits + 1)
        response_class = HttpResponsePermanentRedirect if redirect_rule.permanent else HttpResponseRedirect
        return response_class(redirect_rule.new_path)
    raise Http404


def search(request):
    query = request.GET.get("q", "").strip()
    results = published_articles().none()
    if query:
        if is_arabic():
            results = published_articles().filter(
                Q(title_ar__icontains=query)
                | Q(excerpt_ar__icontains=query)
                | Q(body_ar__icontains=query)
                | Q(focus_keyword_ar__icontains=query)
            )[:30]
        else:
            results = published_articles().filter(
                Q(title__icontains=query)
                | Q(excerpt__icontains=query)
                | Q(body__icontains=query)
                | Q(focus_keyword__icontains=query)
            )[:30]
    return render(
        request,
        "content/search.html",
        page_context(
            request,
            query=query,
            results=results,
            page_title=(f"نتائج البحث عن {query}" if query else "بحث") if is_arabic() else (f"Search results for {query}" if query else "Search"),
            page_description=("ابحث في توقعات Elliott Wave Monitor والتحليلات والمحتوى التعليمي." if is_arabic() else "Search Elliott Wave Monitor forecasts, analysis and trading education."),
        ),
    )


def contact(request):
    page = Page.objects.filter(slug="contact-us", status="published").first()
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form_rate_limited(request, "contact", 10):
            return HttpResponse(ui_text("Too many requests. Please try again later."), status=429)
        contact_message = form.save()
        recipient = SiteSettings.load().contact_email
        if settings.CONTACT_EMAIL_NOTIFICATIONS and recipient:
            try:
                EmailMessage(
                    subject=f"EWM contact: {contact_message.subject}",
                    body=f"From: {contact_message.name} <{contact_message.email}>\n\n{contact_message.message}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient],
                    reply_to=[contact_message.email],
                ).send(fail_silently=False)
            except Exception:
                logging.getLogger(__name__).exception("Contact notification failed; message %s remains saved in admin", contact_message.pk)
        messages.success(request, ui_text("Thanks — your message has been received."))
        return redirect("contact")
    return render(
        request,
        "content/contact.html",
        page_context(
            request,
            page,
            page=page,
            form=form,
            page_title=page.localized_seo_title if page else ui_text("Contact us"),
            page_description=(page.localized_seo_description if page else ("تواصل مع Elliott Wave Monitor." if is_arabic() else "Contact Elliott Wave Monitor.")),
        ),
    )


@require_POST
def newsletter_subscribe(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        if form_rate_limited(request, "newsletter", 20):
            return HttpResponse(ui_text("Too many requests. Please try again later."), status=429)
        email = form.cleaned_data["email"]
        existing = NewsletterSubscriber.objects.filter(email__iexact=email).first()
        if existing:
            existing.is_active = True
            existing.save(update_fields=["is_active"])
        else:
            NewsletterSubscriber.objects.get_or_create(email=email, defaults={"is_active": True})
        messages.success(request, ui_text("You're subscribed to EWM updates."))
    else:
        messages.error(request, ui_text("Please enter a valid email address."))
    destination = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destination = reverse("home")
    return redirect(destination or reverse("home"))


def robots_txt(request):
    if not settings.SITE_INDEXING_ENABLED:
        return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain; charset=utf-8")
    body = """User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: {site}/sitemap.xml
""".format(site=settings.SITE_URL)
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def llms_txt(request):
    settings_obj = SiteSettings.load()
    lines = [
        f"# {settings_obj.display_site_name}",
        "",
        f"> {settings_obj.display_tagline}",
        "",
        "## Core sections",
    ]
    lines.extend(f"- [{category.display_name}]({settings.SITE_URL}{category.get_absolute_url()})" for category in Category.objects.filter(is_visible=True))
    lines.extend(["", "## Latest analysis"])
    lines.extend(f"- [{article.display_title}]({settings.SITE_URL}{article.get_absolute_url()}): {article.display_excerpt[:180]}" for article in published_articles()[:20])
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def health(request):
    return JsonResponse({"status": "ok", "service": "elliott-wave-monitor"})


def error_404(request, exception):
    return render(request, "404.html", page_context(request, page_title=("الصفحة غير موجودة" if is_arabic() else "Page not found")), status=404)


def error_500(request):
    return render(request, "500.html", {"page_title": ("حدث خطأ ما" if is_arabic() else "Something went wrong")}, status=500)
