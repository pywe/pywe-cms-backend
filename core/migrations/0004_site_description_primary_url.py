from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_site"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="site",
            name="primary_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
