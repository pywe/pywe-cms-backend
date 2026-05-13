# Generated for the Page model (PR 3 of the page-sections architecture).
# Hand-written to mirror the 0014_siteprofile migration's style; safe to
# regenerate with `makemigrations` — Django will produce an equivalent file.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_siteprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.CharField(blank=True, default='', max_length=255)),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=16)),
                ('body', models.TextField(blank=True, default='')),
                ('seo', models.JSONField(blank=True, default=dict)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='core.site')),
            ],
            options={
                'db_table': 'site_page',
                'ordering': ['slug', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='page',
            constraint=models.UniqueConstraint(fields=('site', 'slug'), name='uniq_site_page_slug'),
        ),
    ]
