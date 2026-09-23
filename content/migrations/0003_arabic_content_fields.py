from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content", "0002_article_editor_defaults")]

    operations = [
        migrations.AddField(model_name="sitesettings", name="site_name_ar", field=models.CharField(blank=True, max_length=100, verbose_name="Arabic site name")),
        migrations.AddField(model_name="sitesettings", name="tagline_ar", field=models.CharField(blank=True, max_length=180, verbose_name="Arabic tagline")),
        migrations.AddField(model_name="sitesettings", name="hero_title_ar", field=models.CharField(blank=True, max_length=180, verbose_name="Arabic hero title")),
        migrations.AddField(model_name="sitesettings", name="hero_text_ar", field=models.TextField(blank=True, verbose_name="Arabic hero text")),
        migrations.AddField(model_name="sitesettings", name="footer_disclaimer_ar", field=models.TextField(blank=True, verbose_name="Arabic footer disclaimer")),
        migrations.AddField(model_name="category", name="name_ar", field=models.CharField(blank=True, max_length=120, verbose_name="Arabic name")),
        migrations.AddField(model_name="category", name="short_description_ar", field=models.TextField(blank=True, verbose_name="Arabic short description")),
        migrations.AddField(model_name="category", name="body_ar", field=models.TextField(blank=True, help_text="Arabic guide shown on the main-language page.", verbose_name="Arabic evergreen guide")),
        migrations.AddField(model_name="category", name="meta_title_ar", field=models.CharField(blank=True, max_length=70, verbose_name="Arabic SEO title")),
        migrations.AddField(model_name="category", name="meta_description_ar", field=models.CharField(blank=True, max_length=320, verbose_name="Arabic meta description")),
        migrations.AddField(model_name="category", name="social_title_ar", field=models.CharField(blank=True, max_length=100, verbose_name="Arabic social title")),
        migrations.AddField(model_name="category", name="social_description_ar", field=models.CharField(blank=True, max_length=240, verbose_name="Arabic social description")),
        migrations.AddField(model_name="page", name="title_ar", field=models.CharField(blank=True, max_length=180, verbose_name="Arabic title")),
        migrations.AddField(model_name="page", name="eyebrow_ar", field=models.CharField(blank=True, max_length=80, verbose_name="Arabic eyebrow")),
        migrations.AddField(model_name="page", name="excerpt_ar", field=models.TextField(blank=True, verbose_name="Arabic excerpt")),
        migrations.AddField(model_name="page", name="body_ar", field=models.TextField(blank=True, verbose_name="Arabic body")),
        migrations.AddField(model_name="page", name="meta_title_ar", field=models.CharField(blank=True, max_length=70, verbose_name="Arabic SEO title")),
        migrations.AddField(model_name="page", name="meta_description_ar", field=models.CharField(blank=True, max_length=320, verbose_name="Arabic meta description")),
        migrations.AddField(model_name="page", name="social_title_ar", field=models.CharField(blank=True, max_length=100, verbose_name="Arabic social title")),
        migrations.AddField(model_name="page", name="social_description_ar", field=models.CharField(blank=True, max_length=240, verbose_name="Arabic social description")),
        migrations.AddField(model_name="menuitem", name="label_ar", field=models.CharField(blank=True, max_length=80, verbose_name="Arabic label")),
    ]
