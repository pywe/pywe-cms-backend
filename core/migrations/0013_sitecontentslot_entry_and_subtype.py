# Add "entry" slot type and a `subtype` column to SiteContentSlot.
#
# `subtype` is empty by default and only carries a value for entry rows (e.g.
# "project", "news"). The manager owns the catalogue of supported subtypes;
# the backend only validates slug shape.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_sitemedia_group"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitecontentslot",
            name="key",
            field=models.SlugField(
                max_length=64,
                choices=[
                    ("hero", "Hero"),
                    ("about", "About"),
                    ("footer", "Footer"),
                    ("announcement", "Announcement / banner"),
                    ("contact", "Contact / call to action"),
                    ("entry", "Entry"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="sitecontentslot",
            name="subtype",
            field=models.SlugField(
                max_length=64,
                blank=True,
                default="",
                db_index=True,
            ),
        ),
    ]
