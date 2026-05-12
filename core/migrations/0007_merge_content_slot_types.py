# Merge tagline → hero and legal → footer; then narrow slot key choices.

import json

from django.db import migrations, models


def merge_slot_types_forwards(apps, schema_editor):
    SiteContentSlot = apps.get_model("core", "SiteContentSlot")

    def tagline_text(body: str) -> str:
        raw = body or ""
        t = raw.strip()
        if not t:
            return ""
        try:
            j = json.loads(t)
            if isinstance(j, dict) and "text" in j:
                return str(j.get("text") or "").strip()
        except json.JSONDecodeError:
            pass
        return t

    def legal_text(body: str) -> str:
        raw = body or ""
        t = raw.strip()
        if not t:
            return ""
        try:
            j = json.loads(t)
            if isinstance(j, dict) and "body" in j:
                return str(j.get("body") or "").strip()
        except json.JSONDecodeError:
            pass
        return t

    for slot in list(SiteContentSlot.objects.filter(key="tagline")):
        text = tagline_text(slot.body)
        hero = SiteContentSlot.objects.filter(site_id=slot.site_id, key="hero").first()
        if hero:
            raw_h = (hero.body or "").strip()
            try:
                data = json.loads(raw_h) if raw_h else {}
                if not isinstance(data, dict):
                    data = {}
            except json.JSONDecodeError:
                data = {"supporting": raw_h} if raw_h else {}
            if text and not str(data.get("tagline") or "").strip():
                data["tagline"] = text
            hero.body = json.dumps(data)
            hero.save()
        elif text:
            SiteContentSlot.objects.create(
                site_id=slot.site_id,
                key="hero",
                label="Hero",
                body=json.dumps({"tagline": text}),
            )
        slot.delete()

    for slot in list(SiteContentSlot.objects.filter(key="legal")):
        ltext = legal_text(slot.body)
        footer = SiteContentSlot.objects.filter(site_id=slot.site_id, key="footer").first()
        if footer:
            raw_f = (footer.body or "").strip()
            try:
                data = json.loads(raw_f) if raw_f else {}
                if not isinstance(data, dict):
                    data = {}
            except json.JSONDecodeError:
                data = {"body": raw_f} if raw_f else {}
            if ltext and not str(data.get("legalBody") or "").strip():
                data["legalBody"] = ltext
            footer.body = json.dumps(data)
            footer.save()
        elif ltext:
            SiteContentSlot.objects.create(
                site_id=slot.site_id,
                key="footer",
                label="Footer",
                body=json.dumps({"legalBody": ltext}),
            )
        slot.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_sitecontentslot_key_choices"),
    ]

    operations = [
        migrations.RunPython(merge_slot_types_forwards, migrations.RunPython.noop),
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
                ],
            ),
        ),
    ]
