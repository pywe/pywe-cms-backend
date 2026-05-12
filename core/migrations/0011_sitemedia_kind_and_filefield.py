# Generated manually for image/video library kinds.

import core.entities.sites.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_alter_sitecontentslot_options_alter_sitemedia_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitemedia",
            name="kind",
            field=models.CharField(
                choices=[("image", "Image"), ("video", "Video")],
                default="image",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="sitemedia",
            name="file",
            field=models.FileField(
                max_length=500,
                upload_to=core.entities.sites.models.site_media_upload_to,
            ),
        ),
    ]
