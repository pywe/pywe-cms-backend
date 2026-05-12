# Allow multiple content slots per site and type (remove uniqueness on site+key).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_merge_content_slot_types"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="sitecontentslot",
            name="uniq_site_content_slot_site_key",
        ),
    ]
