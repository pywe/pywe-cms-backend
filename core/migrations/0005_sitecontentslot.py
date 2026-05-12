# Generated manually for SiteContentSlot

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_site_description_primary_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteContentSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.SlugField(max_length=64)),
                ("label", models.CharField(blank=True, default="", max_length=255)),
                ("body", models.TextField(blank=True, default="")),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_slots",
                        to="core.site",
                    ),
                ),
            ],
            options={
                "db_table": "site_content_slot",
            },
        ),
        migrations.AddConstraint(
            model_name="sitecontentslot",
            constraint=models.UniqueConstraint(fields=("site", "key"), name="uniq_site_content_slot_site_key"),
        ),
    ]
