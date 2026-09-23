from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Page, SiteSettings


PAGES = {
    "privacy-policy": {
        "title": "Privacy Policy",
        "title_ar": "سياسة الخصوصية",
        "meta_description": "Read Elliott Wave Monitor's Privacy Policy covering personal data, cookies, retention, security and your privacy.",
        "meta_description_ar": "اطلع على سياسة خصوصية Elliott Wave Monitor المتعلقة بالبيانات الشخصية وملفات تعريف الارتباط والاحتفاظ بالمعلومات وأمنها.",
    },
    "terms-conditions": {
        "title": "Terms and Conditions",
        "title_ar": "الشروط والأحكام",
        "meta_description": "Read the terms governing Elliott Wave Monitor, market information, third-party links, service access and intellectual property.",
        "meta_description_ar": "اقرأ شروط استخدام Elliott Wave Monitor المتعلقة بمعلومات الأسواق وروابط الأطراف الثالثة والوصول إلى الخدمات والملكية الفكرية.",
    },
}


class Command(BaseCommand):
    help = "Import the owner-supplied legal pages and their Arabic translations. Existing editorial content is protected unless --overwrite is given."

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true", help="Replace existing legal page content with the bundled source and translation.")

    @transaction.atomic
    def handle(self, *args, **options):
        for slug, metadata in PAGES.items():
            values = dict(metadata)
            for language, field in (("en", "body"), ("ar", "body_ar")):
                source = settings.BASE_DIR / "data" / "pages" / f"{slug}.{language}.html"
                if not source.exists():
                    raise CommandError(f"Missing legal source: {source}")
                values[field] = source.read_text(encoding="utf-8").strip()
            values.update(
                status="published",
                show_in_sitemap=True,
                excerpt=values["meta_description"],
                excerpt_ar=values["meta_description_ar"],
                meta_title=values["title"],
                meta_title_ar=values["title_ar"],
            )
            if options["overwrite"]:
                Page.objects.update_or_create(slug=slug, defaults=values)
                self.stdout.write(self.style.SUCCESS(f"Restored both editions: {slug}"))
            else:
                _, created = Page.objects.get_or_create(slug=slug, defaults=values)
                self.stdout.write(f"{'Created' if created else 'Preserved existing page'}: {slug}")

        contact, _ = Page.objects.get_or_create(
            slug="contact-us",
            defaults={"title": "Contact Us", "title_ar": "اتصل بنا", "status": "published"},
        )
        if not contact.body.strip():
            contact.body = (
                '<h2>Get in touch with the EWM Team</h2>'
                '<p>For editorial questions, feedback and business enquiries, use the form below '
                'or email <a href="mailto:elliottwavemonitor@gmail.com">elliottwavemonitor@gmail.com</a>.</p>'
            )
            contact.save(update_fields=["body", "updated_at"])
        site = SiteSettings.load()
        if not site.contact_email:
            site.contact_email = "elliottwavemonitor@gmail.com"
            site.save(update_fields=["contact_email", "updated_at"])
