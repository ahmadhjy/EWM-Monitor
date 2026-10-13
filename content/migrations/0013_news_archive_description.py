from django.db import migrations


def fill_news_description(apps, schema_editor):
    # Fill only missing English metadata; preserve editor-written descriptions.
    apps.get_model("content", "Category").objects.using(schema_editor.connection.alias).filter(
        slug="latest-news-and-analysis", meta_description="", short_description="",
    ).update(meta_description="Read the latest financial news and Elliott Wave analysis covering forex, commodities, cryptocurrencies and stock indices from Elliott Wave Monitor.")


class Migration(migrations.Migration):
    dependencies = [("content", "0012_alter_sitesettings_footer_logo")]
    operations = [migrations.RunPython(fill_news_description, migrations.RunPython.noop)]
