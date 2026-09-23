from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="excerpt",
            field=models.TextField(
                blank=True,
                help_text="Used on cards and below the title. Leave blank to generate the first 15 words automatically.",
            ),
        ),
    ]
