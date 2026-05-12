import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_sitemedia_kind_and_filefield"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteMediaGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=128)),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media_groups",
                        to="core.site",
                    ),
                ),
            ],
            options={
                "db_table": "site_media_group",
                "ordering": ["name", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="sitemediagroup",
            constraint=models.UniqueConstraint(
                fields=("site", "name"),
                name="uniq_site_media_group_site_name",
            ),
        ),
        migrations.AddField(
            model_name="sitemedia",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="media_items",
                to="core.sitemediagroup",
            ),
        ),
    ]
