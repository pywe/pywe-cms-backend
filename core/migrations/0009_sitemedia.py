import uuid
from pathlib import Path

import django.db.models.deletion
from django.db import migrations, models


def upload_to(instance, filename):
    suf = Path(filename).suffix.lower()[:12] or ""
    if not suf or len(suf) > 10:
        suf = ".bin"
    return f"site_media/{instance.site_id}/{uuid.uuid4().hex}{suf}"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_sitecontentslot_allow_multiple_per_key"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("file", models.ImageField(max_length=500, upload_to=upload_to)),
                ("original_name", models.CharField(blank=True, default="", max_length=255)),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media_files",
                        to="core.site",
                    ),
                ),
            ],
            options={
                "db_table": "site_media",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
