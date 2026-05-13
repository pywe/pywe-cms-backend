# Retire the legacy "About" content slot type. About is now composed via the
# generic `Page` model + section kinds (@pywe/cms-sections), so the dedicated
# slot kind is no longer offered in the manager.
#
# Forwards:
#   1. Delete any `SiteContentSlot` rows with `key="about"` (the manager has
#      already removed the UI to view/edit them, and there is no public-site
#      renderer for them in the new alignment).
#   2. Narrow the `key` choices to drop "about".
#
# Backwards: re-widen the choices to include "about" again. We intentionally
# do NOT restore deleted rows — that's not recoverable without backups.

from django.db import migrations, models


def delete_about_slots_forwards(apps, schema_editor):
    SiteContentSlot = apps.get_model("core", "SiteContentSlot")
    SiteContentSlot.objects.filter(key="about").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_page"),
    ]

    operations = [
        migrations.RunPython(delete_about_slots_forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sitecontentslot",
            name="key",
            field=models.SlugField(
                max_length=64,
                choices=[
                    ("hero", "Hero"),
                    ("footer", "Footer"),
                    ("announcement", "Announcement / banner"),
                    ("contact", "Contact / call to action"),
                    ("entry", "Entry"),
                ],
            ),
        ),
    ]
