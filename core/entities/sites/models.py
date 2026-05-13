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


class SiteProfile(TimeStamp):
    """Site-wide identity, SEO, contact and configuration settings (1:1 with Site).

    All fields are optional. The manager renders the profile as grouped cards
    (identity, SEO, contact, social, navigation, locale, theme, operations) so
    workspace owners can fill in what they have without being blocked by what
    they don't.

    `nav_links` is a JSON list of `{"label": str, "path": str}` entries.
    `contact_topics` is a JSON list of strings used to populate the contact
    form topic select. Robots/maintenance booleans default to safe values
    (`robots_index=True`, `maintenance_enabled=False`).
    """

    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    display_name = models.CharField(max_length=200, blank=True, default="")
    short_name = models.CharField(max_length=20, blank=True, default="")
    tagline = models.CharField(max_length=200, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    logo = models.ForeignKey(
        "SiteMedia",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    favicon = models.ForeignKey(
        "SiteMedia",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    canonical_url = models.URLField(max_length=500, blank=True, default="")
    seo_title = models.CharField(max_length=200, blank=True, default="")
    title_template = models.CharField(max_length=200, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")
    og_image = models.ForeignKey(
        "SiteMedia",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    robots_index = models.BooleanField(default=True)
    twitter_handle = models.CharField(max_length=64, blank=True, default="")

    contact_email = models.EmailField(max_length=254, blank=True, default="")
    contact_phone = models.CharField(max_length=64, blank=True, default="")
    contact_address = models.TextField(blank=True, default="")
    contact_region = models.CharField(max_length=200, blank=True, default="")
    contact_consent_text = models.TextField(blank=True, default="")
    contact_topics = models.JSONField(blank=True, default=list)

    social_facebook = models.URLField(max_length=500, blank=True, default="")
    social_x = models.URLField(max_length=500, blank=True, default="")
    social_instagram = models.URLField(max_length=500, blank=True, default="")
    social_linkedin = models.URLField(max_length=500, blank=True, default="")
    social_youtube = models.URLField(max_length=500, blank=True, default="")
    social_whatsapp = models.URLField(max_length=500, blank=True, default="")

    nav_links = models.JSONField(blank=True, default=list)
    nav_cta_label = models.CharField(max_length=64, blank=True, default="")
    nav_cta_path = models.CharField(max_length=200, blank=True, default="")

    html_lang = models.CharField(max_length=16, blank=True, default="en")
    og_locale = models.CharField(max_length=16, blank=True, default="")
    timezone = models.CharField(max_length=64, blank=True, default="")
    date_format = models.CharField(max_length=32, blank=True, default="")

    primary_color = models.CharField(max_length=20, blank=True, default="")
    accent_color = models.CharField(max_length=20, blank=True, default="")
    heading_font = models.CharField(max_length=100, blank=True, default="")
    body_font = models.CharField(max_length=100, blank=True, default="")

    analytics_id = models.CharField(max_length=120, blank=True, default="")
    maintenance_enabled = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True, default="")
    copyright_name = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        app_label = "core"
        db_table = "site_profile"

    def __str__(self) -> str:
        return f"{self.site.slug} profile"


class SiteContentSlot(TimeStamp):
    """Content block for a site. `key` is the slot type; many rows may share the same (site, key).

    `subtype` is only meaningful when `key == "entry"`. It carries the user-facing
    kind of the entry (e.g. "project", "news", "case-study") so the manager can
    surface those as distinct content types. The catalogue of supported subtypes
    is owned by the manager — the backend only validates slug shape and stores
    whatever it receives. For non-entry slots the column is empty.
    """

    class SlotType(models.TextChoices):
        HERO = "hero", _("Hero")
        FOOTER = "footer", _("Footer")
        ANNOUNCEMENT = "announcement", _("Announcement / banner")
        CONTACT = "contact", _("Contact / call to action")
        ENTRY = "entry", _("Entry")

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="content_slots")
    key = models.SlugField(max_length=64, choices=SlotType.choices)
    subtype = models.SlugField(max_length=64, blank=True, default="", db_index=True)
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


class Page(TimeStamp):
    """A composable page on a site, rendered as an ordered list of typed sections.

    `body` is a JSON envelope of the shape:
        {"v": 1, "sections": [{"id": str, "kind": str, "value": str}, ...]}
    The catalogue of valid `kind` values lives in the `@pywe/cms-sections`
    workspace package (consumed by the Svelte manager and the Next.js public
    frontend); the backend only enforces the envelope shape and stores
    `body` verbatim so new kinds can ship without a backend deploy.

    `slug` is a free CharField rather than a SlugField because pages support
    nested paths (e.g. `press/2026-q1`). The empty string represents the
    homepage (URL `/`). Slug shape is validated by the serializer.

    `seo` is a JSON dict; the serializer keeps the documented keys
    (`description`, `ogImage`, `noindex`) and drops unknown ones.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="pages")
    slug = models.CharField(max_length=255, blank=True, default="")
    title = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    body = models.TextField(blank=True, default="")
    seo = models.JSONField(blank=True, default=dict)

    class Meta:
        app_label = "core"
        db_table = "site_page"
        ordering = ["slug", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["site", "slug"],
                name="uniq_site_page_slug",
            ),
        ]

    def __str__(self) -> str:
        display_slug = self.slug or "/"
        if self.pk:
            return f"{self.site.slug}:{display_slug}#{self.pk}"
        return f"{self.site.slug}:{display_slug}"


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
# `entry` is intentionally omitted: the manager exposes its subtypes (project, news, …)
# as distinct content types via its own kind registry, not as a single "Entry" card.
CONTENT_SLOT_TYPE_HINTS: dict[str, str] = {
    "hero": "Compose the hero from optional sections (eyebrow, headline, subheadline, copy, background image from Media, buttons). Add only what you need.",
    "footer": "Footer links and copy, plus optional legal or compliance text.",
    "announcement": "Site-wide banner or alert message.",
    "contact": "Contact block, address, or primary call to action.",
}
