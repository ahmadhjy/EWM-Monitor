from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0007_alter_menuitem_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="footer_logo",
            field=models.ImageField(
                "Footer logo", upload_to="branding/footer/", blank=True,
                help_text="Optional logo for the dark footer. Use a tightly cropped, transparent PNG or WebP with white/light artwork. It fits within 165 × 76 px without stretching. Leave blank to keep the existing footer logo.",
            ),
        ),
    ]
