import uuid
from pathlib import Path

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.entities.common.models import TimeStamp
from core.entities.workspaces.models import Workspace


class SiteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)


class SiteManager(models.Manager):
    def get_queryset(self):
        return SiteQuerySet(self.model, using=self._db).alive()


class Site(TimeStamp):
    """A site belongs to one workspace; many sites per workspace. Soft-deleted rows keep history."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="sites",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=96)
    description = models.TextField(blank=True, default="")
    primary_url = models.URLField(max_length=500, blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SiteManager()
    all_objects = models.Manager()

    class Meta:
        app_label = "core"
        db_table = "site"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_site_workspace_slug_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class SiteContentSlot(TimeStamp):
    """Content block for a site. `key` is the slot type; many rows may share the same (site, key)."""

    class SlotType(models.TextChoices):
        HERO = "hero", _("Hero")
        ABOUT = "about", _("About")
        FOOTER = "footer", _("Footer")
        ANNOUNCEMENT = "announcement", _("Announcement / banner")
        CONTACT = "contact", _("Contact / call to action")

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="content_slots")
    key = models.SlugField(max_length=64, choices=SlotType.choices)
    label = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")

    class Meta:
        app_label = "core"
        db_table = "site_content_slot"
        ordering = ["key", "id"]

    def __str__(self) -> str:
        if self.pk:
            return f"{self.site.slug}:{self.key}#{self.pk}"
        return f"{self.site.slug}:{self.key}"


def site_media_upload_to(instance: "SiteMedia", filename: str) -> str:
    suf = Path(filename).suffix.lower()[:12] or ""
    if not suf or len(suf) > 10:
        suf = ".bin"
    return f"site_media/{instance.site_id}/{uuid.uuid4().hex}{suf}"


class SiteMediaGroup(TimeStamp):
    """Logical folder for site media (images/videos); optional on each SiteMedia row."""

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="media_groups")
    name = models.CharField(max_length=128)

    class Meta:
        app_label = "core"
        db_table = "site_media_group"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["site", "name"],
                name="uniq_site_media_group_site_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.site.slug}:{self.name}"


class SiteMedia(TimeStamp):
    """Image or video stored for a site; referenced from content (e.g. hero background) as `media:<id>`."""

    class MediaKind(models.TextChoices):
        IMAGE = "image", _("Image")
        VIDEO = "video", _("Video")

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="media_files")
    group = models.ForeignKey(
        "SiteMediaGroup",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="media_items",
    )
    kind = models.CharField(
        max_length=10,
        choices=MediaKind.choices,
        default=MediaKind.IMAGE,
    )
    file = models.FileField(upload_to=site_media_upload_to, max_length=500)
    original_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        app_label = "core"
        db_table = "site_media"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        if self.pk:
            return f"{self.site.slug}:media#{self.pk}"
        return f"{self.site.slug}:media"


# Manager API hints for each slot type (keep keys in sync with SiteContentSlot.SlotType).
CONTENT_SLOT_TYPE_HINTS: dict[str, str] = {
    "hero": "Compose the hero from optional sections (eyebrow, headline, subheadline, copy, background image from Media, buttons). Add only what you need.",
    "about": "Structured About copy: intro, story, mission, team, trust, and optional call to action.",
    "footer": "Footer links and copy, plus optional legal or compliance text.",
    "announcement": "Site-wide banner or alert message.",
    "contact": "Contact block, address, or primary call to action.",
}
