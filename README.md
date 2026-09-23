# Elliott Wave Monitor — Django rebuild

A performance-first Django replacement for the WordPress/Oxygen site at `elliottwavemonitor.com`.

## What is included

- Responsive public site with a navy/gold editorial design, lightweight interactions, accessible navigation, and no front-end framework dependency.
- Arabic is the main, unprefixed language with a fully responsive RTL interface; the English version remains available under `/en/`. Fifteen market news and analysis articles have complete Arabic editions. Education articles remain English-only and are excluded from Arabic listings, search, routes, and sitemap alternates until editors add an Arabic edition.
- Django 5.2 LTS content system with the Unfold admin dashboard and a full TinyMCE editor.
- Article workflow with drafts, scheduling, categories, featured/trending flags, featured images, inline rich media, author and publication controls.
- Yoast-equivalent SEO fields: SEO title, meta description, focus keyword, canonical URL, robots controls, Open Graph title/description/image, clean slugs, and preview-ready defaults.
- Dynamic XML sitemap, RSS feed, `robots.txt`, `llms.txt`, canonical metadata, Article/Organization/WebSite structured data, breadcrumbs, and redirect management.
- Contact messages, newsletter subscribers, media library, menu editor, site settings, legal pages, and reusable archive pages.
- Public WordPress migration snapshot with 20 articles, 3 standalone pages, 13 categories, and 206 media-library records.
- The complete evergreen information sections from all six legacy currency forecast pages are preserved below their current analysis feeds and remain editable in the category admin.
- The original EWM wordmark and favicon are restored from the WordPress media library as exact, lightweight SVG vectors.
- All public article and inline images are copied locally. Data-preserving high-resolution WebP restorations keep chart labels and price levels intact, with separate card, mobile, compact, and 1920×1200 hero variants.
- Production settings for PostgreSQL, WhiteNoise, HTTPS, secure cookies, HSTS, Gunicorn, and Nginx.

## Local preview

The preview is already running at:

- Public site: <http://127.0.0.1:8010/>
- English version: <http://127.0.0.1:8010/en/>
- Editorial admin: <http://127.0.0.1:8010/admin/>

The admin interface is always English and left-to-right. The local administrator username is `ewmadmin`; passwords are not stored in this repository. Production receives a separate, randomly generated password.

To start it again later in PowerShell:

```powershell
cd website
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8010
```

## Rebuilding the local database

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_wordpress_snapshot --download-media
.\.venv\Scripts\python.exe manage.py import_currency_sections
.\.venv\Scripts\python.exe manage.py populate_arabic_content
.\.venv\Scripts\python.exe manage.py populate_arabic_articles
.\.venv\Scripts\python.exe manage.py populate_support_pages --overwrite
.\.venv\Scripts\python.exe manage.py optimize_images
.\.venv\Scripts\python.exe manage.py createsuperuser
```

The import is idempotent: articles, pages, categories, and media records are matched to their WordPress IDs or slugs and updated safely.

## Editorial workflow

1. Open **Articles** in the admin.
2. Create or edit an article with the rich text toolbar. Add both the Arabic and English editions when it should appear in both languages. A blank excerpt is generated from the first 15 words in each language, and the editable author default is **EWM Team**.
3. Use the image tool's browse button to search and reuse the website media library, upload a new image, and set or update its alt text before inserting it.
4. Choose the primary category, featured image, publication state/date, and optional featured/trending placement.
5. Open the collapsed **Search & social preview** section to set Yoast-style fields.
6. Use **View on site** before publishing.

To manually translate an existing English article, open **Articles**, select the article, and scroll to **Arabic translation**. Enter **Arabic title** and **Arabic body**, optionally add an Arabic excerpt, image alt text, and Arabic SEO fields, then save. Both title and body must be present before the article appears on Arabic pages. The **Arabic edition** column shows which articles have a translation. Education remains English-only until editors complete these fields.

Collected emails appear under **Newsletter subscribers** in the sidebar. Duplicate addresses are consolidated case-insensitively. Contact messages appear under **Messages**; email notifications are disabled until delivery credentials are configured.

Global brand copy, social links, contact email, analytics ID, verification token, and the risk disclaimer live under **Site settings**. Navigation is editable under **Navigation**. Old URL changes can be handled under **Redirects** without code changes.

## Verification completed

- Django system check: clean.
- Automated tests: 21 passed, including language isolation, English admin, translation fields, subscriber deduplication, CSRF, spam rejection, protected media access, and complete bilingual legal content.
- Public routes, admin login, sitemap, RSS, robots, AI discovery, and health endpoint: verified locally.
- Browser console errors: none on desktop or mobile previews.
- Earlier local Lighthouse audits achieved 99–100 Performance and 100 Accessibility / Best Practices / SEO. Re-run audits after deployment; scores vary with environment and content.

The release browser pass covered 138 page/viewport combinations and 155 images with no failures after legacy education links were made language-aware. The owner supplied the original legal text; both complete English pages and their Arabic translations are restored. See [legal source review](docs/LEGAL-SOURCE-REVIEW.md) for source inconsistencies that need owner review before domain launch.

Local Lighthouse is a controlled lab result, not a permanent guarantee. Production scores still depend on Droplet load, network location, analytics/advertising tags, DNS/CDN configuration, and future editorial image choices. The included Nginx caching and image workflow are designed to preserve these results.

## Production deployment

See [`deploy/README.md`](deploy/README.md) for the DigitalOcean runbook. Do not point the domain at the Droplet until the production database, media directory, SSL certificate, backups, email delivery, analytics consent requirements, and URL crawl have been verified.
