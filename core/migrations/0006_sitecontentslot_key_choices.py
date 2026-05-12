# Restrict SiteContentSlot.key to predefined slot types.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_sitecontentslot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitecontentslot",
            name="key",
            field=models.SlugField(
                max_length=64,
                choices=[
                    ("hero", "Hero"),
                    ("tagline", "Tagline"),
                    ("about", "About"),
                    ("footer", "Footer"),
                    ("legal", "Legal & policies"),
                    ("announcement", "Announcement / banner"),
                    ("contact", "Contact / call to action"),
                ],
            ),
        ),
    ]
