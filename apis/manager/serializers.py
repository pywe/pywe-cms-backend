import json
import re
from pathlib import Path

from django.utils.text import slugify
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from core.entities.sites.models import (
    Page,
    Site,
    SiteContentSlot,
    SiteMedia,
    SiteMediaGroup,
    SiteProfile,
)
from core.entities.users.models import Account
from core.entities.workspaces.models import Workspace

_WORKSPACE_SLUG_RESERVED = frozenset(
    {"admin", "api", "client", "manager", "content", "static", "media"},
)


def unique_workspace_slug_from_name(name: str) -> str:
    """Return a URL-safe slug derived from display name (unique + not reserved)."""
    base = slugify(name.strip()) or "workspace"
    base = base[:80]
    candidate = base
    counter = 2
    while True:
        lower = candidate.lower()
        if lower not in _WORKSPACE_SLUG_RESERVED and not Workspace.objects.filter(slug=candidate).exists():
            return candidate[:96]
        suffix = f"-{counter}"
        candidate = (base[: max(1, 96 - len(suffix))] + suffix)[:96]
        counter += 1


class ManagerRegisterSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_phone_number(self, value):
        if Account.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("An account with this phone already exists.")
        return value

    def create(self, validated_data):
        return Account.objects.create_user(
            phone_number=validated_data["phone_number"],
            password=validated_data["password"],
        )


class ManagerOtpRequestSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()


class ManagerOtpVerifySerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        max_length=6,
        min_length=6,
        error_messages={"invalid": "Code must be a 6-digit number."},
    )


class ManagerProfilePatchSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("First name is required.")
        return value.strip()

    def validate_last_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Last name is required.")
        return value.strip()

    def validate_email(self, value):
        return value.strip().lower()


class WorkspaceCreateSerializer(serializers.Serializer):
    """Create payload: display name only; slug is generated server-side from the name."""

    name = serializers.CharField(max_length=255)

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()

    def validate(self, attrs):
        attrs["slug"] = unique_workspace_slug_from_name(attrs["name"])
        return attrs


class WorkspaceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ("id", "name", "slug", "is_active", "created_at", "updated_at")


_SITE_SLUG_RESERVED = frozenset(
    {"admin", "api", "client", "manager", "content", "static", "media", "www", "app"},
)


def unique_site_slug_from_name(name: str, workspace: Workspace) -> str:
    """Return a URL-safe slug unique within this workspace (active sites only)."""
    base = slugify(name.strip()) or "site"
    base = base[:80]
    candidate = base
    counter = 2
    while True:
        lower = candidate.lower()
        if lower not in _SITE_SLUG_RESERVED:
            if not Site.objects.filter(workspace=workspace, slug=candidate).exists():
                return candidate[:96]
        suffix = f"-{counter}"
        candidate = (base[: max(1, 96 - len(suffix))] + suffix)[:96]
        counter += 1


class SiteReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ("id", "name", "slug", "description", "primary_url", "created_at", "updated_at")


class SiteCreateSerializer(serializers.Serializer):
    """Create: name required; slug is generated server-side. Optional description and public URL."""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    primary_url = serializers.URLField(required=False, allow_blank=True, max_length=500)

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()

    def validate_description(self, value: str) -> str:
        return (value or "").strip()

    def validate_primary_url(self, value: str) -> str:
        return (value or "").strip()

    def validate(self, attrs):
        workspace: Workspace = self.context["workspace"]
        attrs["slug"] = unique_site_slug_from_name(attrs["name"], workspace)
        return attrs


class SitePatchSerializer(serializers.ModelSerializer):
    """Update display fields only; slug is stable and comes from the URL."""

    class Meta:
        model = Site
        fields = ("name", "description", "primary_url")

    def validate_name(self, value: str) -> str:
        if not value or not str(value).strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return str(value).strip()

    def validate_description(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def validate_primary_url(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value).strip()


class SiteContentSlotReadSerializer(serializers.ModelSerializer):
    type_label = serializers.SerializerMethodField()

    class Meta:
        model = SiteContentSlot
        fields = (
            "id",
            "key",
            "type_label",
            "subtype",
            "label",
            "body",
            "created_at",
            "updated_at",
        )

    def get_type_label(self, obj: SiteContentSlot) -> str:
        try:
            return str(SiteContentSlot.SlotType(obj.key).label)
        except ValueError:
            return obj.key


class SiteContentSlotCreateSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=SiteContentSlot.SlotType.choices)
    subtype = serializers.SlugField(max_length=64, required=False, allow_blank=True)
    label = serializers.CharField(max_length=255, required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True, max_length=500_000)

    def validate_label(self, value: str) -> str:
        return (value or "").strip()

    def validate_body(self, value: str) -> str:
        return value or ""

    def validate(self, attrs: dict) -> dict:
        # `subtype` is only meaningful for entry slots; force-empty for others.
        if attrs.get("key") != SiteContentSlot.SlotType.ENTRY.value:
            attrs["subtype"] = ""
        else:
            attrs["subtype"] = (attrs.get("subtype") or "").strip()
        return attrs


class SiteContentSlotPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteContentSlot
        fields = ("subtype", "label", "body")

    def validate_label(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def validate_body(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value)

    def validate_subtype(self, value: str | None) -> str:
        return (value or "").strip()

    def validate(self, attrs: dict) -> dict:
        instance = getattr(self, "instance", None)
        if "subtype" in attrs and instance is not None:
            if instance.key != SiteContentSlot.SlotType.ENTRY.value:
                attrs["subtype"] = ""
        return attrs


_SITE_MEDIA_IMAGE_MAX_BYTES = 10 * 1024 * 1024
_SITE_MEDIA_VIDEO_MAX_BYTES = 80 * 1024 * 1024

_SITE_MEDIA_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
_SITE_MEDIA_VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v"}


class SiteMediaReadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = SiteMedia
        fields = ("id", "kind", "url", "original_name", "created_at", "group_id", "group_name")

    def get_url(self, obj: SiteMedia) -> str:
        request = self.context.get("request")
        rel = obj.file.url
        if request is not None:
            return request.build_absolute_uri(rel)
        return rel

    def get_group_id(self, obj: SiteMedia) -> int | None:
        return obj.group_id

    def get_group_name(self, obj: SiteMedia) -> str:
        if obj.group_id is None:
            return ""
        g = getattr(obj, "group", None)
        return g.name if g is not None else ""


class SiteMediaCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    kind = serializers.ChoiceField(choices=("image", "video"), default="image")
    group_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        uploaded = attrs["file"]
        kind = attrs["kind"]
        name = (getattr(uploaded, "name", None) or "")[:512]
        ext = Path(name).suffix.lower()
        size = int(getattr(uploaded, "size", 0) or 0)
        content_type = (getattr(uploaded, "content_type", None) or "").lower()

        if kind == SiteMedia.MediaKind.IMAGE:
            if ext and ext not in _SITE_MEDIA_IMAGE_EXT:
                raise serializers.ValidationError(
                    {"file": "Unsupported image type. Use JPEG, PNG, WebP, GIF, or SVG."},
                )
            if not ext and not content_type.startswith("image/"):
                raise serializers.ValidationError({"file": "Upload a valid image file."})
            if size > _SITE_MEDIA_IMAGE_MAX_BYTES:
                raise serializers.ValidationError({"file": "Image must be 10 MB or smaller."})
        else:
            if ext and ext not in _SITE_MEDIA_VIDEO_EXT:
                raise serializers.ValidationError(
                    {"file": "Unsupported video type. Use MP4, WebM, MOV, or M4V."},
                )
            if not ext and not content_type.startswith("video/"):
                raise serializers.ValidationError({"file": "Upload a valid video file."})
            if size > _SITE_MEDIA_VIDEO_MAX_BYTES:
                raise serializers.ValidationError({"file": "Video must be 80 MB or smaller."})

        gid = attrs.get("group_id")
        site = self.context.get("site")
        if gid is not None and site is not None:
            if not SiteMediaGroup.objects.filter(pk=gid, site=site).exists():
                raise serializers.ValidationError({"group_id": "Unknown group for this site."})

        return attrs


class SiteMediaGroupSerializer(serializers.ModelSerializer):
    media_count = serializers.SerializerMethodField()

    class Meta:
        model = SiteMediaGroup
        fields = ("id", "name", "media_count", "created_at")

    def get_media_count(self, obj: SiteMediaGroup) -> int:
        return int(getattr(obj, "media_count", 0))


class SiteMediaGroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)

    def validate_name(self, value: str) -> str:
        t = str(value or "").strip()
        if not t:
            raise serializers.ValidationError("Name is required.")
        return t[:128]


class SiteMediaGroupPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteMediaGroup
        fields = ("name",)

    def validate_name(self, value: str) -> str:
        t = str(value or "").strip()
        if not t:
            raise serializers.ValidationError("Name is required.")
        return t[:128]


class SiteMediaBulkGroupSerializer(serializers.Serializer):
    media_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1)
    group_id = serializers.IntegerField(required=False, allow_null=True)


class SiteMediaBulkDeleteSerializer(serializers.Serializer):
    media_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1)


class _SiteProfileMediaRefField(serializers.IntegerField):
    """Accept a numeric `SiteMedia` id (or null) that belongs to the contextual site."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        kwargs.setdefault("min_value", 1)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        if data in (None, "", 0, "0"):
            return None
        value = super().to_internal_value(data)
        site = self.context.get("site")
        if site is not None and not SiteMedia.objects.filter(pk=value, site=site).exists():
            raise serializers.ValidationError("Unknown media id for this site.")
        return value


class _SiteProfileNavLinkSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=64, allow_blank=False)
    path = serializers.CharField(max_length=200, allow_blank=False)

    def validate_label(self, value: str) -> str:
        t = str(value or "").strip()
        if not t:
            raise serializers.ValidationError("Label is required.")
        return t

    def validate_path(self, value: str) -> str:
        t = str(value or "").strip()
        if not t:
            raise serializers.ValidationError("Path is required.")
        return t


class SiteProfileReadSerializer(serializers.ModelSerializer):
    logo_id = serializers.SerializerMethodField()
    favicon_id = serializers.SerializerMethodField()
    og_image_id = serializers.SerializerMethodField()

    class Meta:
        model = SiteProfile
        fields = (
            "display_name",
            "short_name",
            "tagline",
            "summary",
            "logo_id",
            "favicon_id",
            "canonical_url",
            "seo_title",
            "title_template",
            "meta_description",
            "og_image_id",
            "robots_index",
            "twitter_handle",
            "contact_email",
            "contact_phone",
            "contact_address",
            "contact_region",
            "contact_consent_text",
            "contact_topics",
            "social_facebook",
            "social_x",
            "social_instagram",
            "social_linkedin",
            "social_youtube",
            "social_whatsapp",
            "nav_links",
            "nav_cta_label",
            "nav_cta_path",
            "html_lang",
            "og_locale",
            "timezone",
            "date_format",
            "primary_color",
            "accent_color",
            "heading_font",
            "body_font",
            "analytics_id",
            "maintenance_enabled",
            "maintenance_message",
            "copyright_name",
            "created_at",
            "updated_at",
        )

    def get_logo_id(self, obj: SiteProfile) -> int | None:
        return obj.logo_id

    def get_favicon_id(self, obj: SiteProfile) -> int | None:
        return obj.favicon_id

    def get_og_image_id(self, obj: SiteProfile) -> int | None:
        return obj.og_image_id


class SiteProfilePatchSerializer(serializers.Serializer):
    """Patch any subset of the profile. All fields are optional on PATCH."""

    display_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    short_name = serializers.CharField(max_length=20, required=False, allow_blank=True)
    tagline = serializers.CharField(max_length=200, required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    logo_id = _SiteProfileMediaRefField()
    favicon_id = _SiteProfileMediaRefField()

    canonical_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    seo_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    title_template = serializers.CharField(max_length=200, required=False, allow_blank=True)
    meta_description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    og_image_id = _SiteProfileMediaRefField()
    robots_index = serializers.BooleanField(required=False)
    twitter_handle = serializers.CharField(max_length=64, required=False, allow_blank=True)

    contact_email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    contact_address = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    contact_region = serializers.CharField(max_length=200, required=False, allow_blank=True)
    contact_consent_text = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    contact_topics = serializers.ListField(
        child=serializers.CharField(max_length=80, allow_blank=False),
        required=False,
        allow_empty=True,
        max_length=20,
    )

    social_facebook = serializers.URLField(max_length=500, required=False, allow_blank=True)
    social_x = serializers.URLField(max_length=500, required=False, allow_blank=True)
    social_instagram = serializers.URLField(max_length=500, required=False, allow_blank=True)
    social_linkedin = serializers.URLField(max_length=500, required=False, allow_blank=True)
    social_youtube = serializers.URLField(max_length=500, required=False, allow_blank=True)
    social_whatsapp = serializers.URLField(max_length=500, required=False, allow_blank=True)

    nav_links = _SiteProfileNavLinkSerializer(many=True, required=False, allow_empty=True)
    nav_cta_label = serializers.CharField(max_length=64, required=False, allow_blank=True)
    nav_cta_path = serializers.CharField(max_length=200, required=False, allow_blank=True)

    html_lang = serializers.CharField(max_length=16, required=False, allow_blank=True)
    og_locale = serializers.CharField(max_length=16, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    date_format = serializers.CharField(max_length=32, required=False, allow_blank=True)

    primary_color = serializers.CharField(max_length=20, required=False, allow_blank=True)
    accent_color = serializers.CharField(max_length=20, required=False, allow_blank=True)
    heading_font = serializers.CharField(max_length=100, required=False, allow_blank=True)
    body_font = serializers.CharField(max_length=100, required=False, allow_blank=True)

    analytics_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    maintenance_enabled = serializers.BooleanField(required=False)
    maintenance_message = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    copyright_name = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def _trim_str(self, value):
        return "" if value is None else str(value).strip()

    def validate_contact_topics(self, value):
        seen: set[str] = set()
        out: list[str] = []
        for item in value or []:
            t = str(item or "").strip()
            if not t:
                continue
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t[:80])
        return out

    def validate_nav_links(self, value):
        seen: set[str] = set()
        out: list[dict] = []
        for entry in value or []:
            label = (entry.get("label") or "").strip() if isinstance(entry, dict) else ""
            path = (entry.get("path") or "").strip() if isinstance(entry, dict) else ""
            if not label or not path:
                continue
            key = path.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"label": label[:64], "path": path[:200]})
        return out

    def validate(self, attrs: dict) -> dict:
        # Trim every string-like value so we don't store leading/trailing spaces.
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = v.strip()
        return attrs

    def apply(self, instance: SiteProfile) -> SiteProfile:
        """Apply validated_data to the instance and save only the fields we touched."""
        data = self.validated_data
        media_field_map = {
            "logo_id": "logo_id",
            "favicon_id": "favicon_id",
            "og_image_id": "og_image_id",
        }
        update_fields: list[str] = []
        for key, value in data.items():
            target = media_field_map.get(key, key)
            setattr(instance, target, value)
            update_fields.append(target)
        if update_fields:
            update_fields.append("updated_at")
            instance.save(update_fields=update_fields)
        return instance


# --------------------------------------------------------------------------- #
# Page (composable page sections)                                              #
# --------------------------------------------------------------------------- #

# Each `/`-delimited segment of a page slug must look like a URL-friendly token.
_PAGE_SLUG_SEGMENT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_PAGE_SLUG_MAX_LEN = 255

# Bump when the body envelope shape changes. Section kinds evolve
# independently (each kind in `@pywe/cms-sections/kinds` versions itself).
_PAGE_BODY_SUPPORTED_VERSIONS = frozenset({1})

# Documented SEO keys. Unknown keys are silently dropped on read+write so
# rolling out a new key is purely additive (manager ships first; backend
# version-bump comes whenever it's convenient).
_PAGE_SEO_KEYS = ("description", "ogImage", "noindex")


def _normalise_page_slug(raw: str | None) -> str:
    """Lowercase, strip surrounding slashes, validate segments.

    Empty string represents the homepage and is returned as-is. Validation
    failures raise `ValidationError`; the caller decides what HTTP status that
    maps to (DRF handles 400 by default).
    """
    s = (raw or "").strip().strip("/").lower()
    if not s:
        return ""
    if len(s) > _PAGE_SLUG_MAX_LEN:
        raise serializers.ValidationError(
            f"Slug is too long (max {_PAGE_SLUG_MAX_LEN} characters)."
        )
    for segment in s.split("/"):
        if not _PAGE_SLUG_SEGMENT_RE.fullmatch(segment):
            raise serializers.ValidationError(
                f"Invalid slug segment {segment!r}: use lowercase letters, "
                "digits, and dashes; separate segments with '/'."
            )
    return s


def _validate_page_body_json(raw: str | None) -> str:
    """Parse and validate the section envelope; return the canonical JSON string.

    Empty payloads are allowed (= empty page). When non-empty, the value must
    parse to `{"v": <supported>, "sections": [{id, kind, value}, ...]}`.
    The serialized string is returned verbatim (no re-serialization) so
    insignificant whitespace round-trips intact, and so unknown extra
    top-level keys (forward-compat additions) survive the trip through the
    backend without losing information.
    """
    s = (raw or "").strip()
    if not s:
        return ""
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError as exc:
        raise serializers.ValidationError(f"body must be valid JSON: {exc.msg}.")
    if not isinstance(parsed, dict):
        raise serializers.ValidationError("body must be a JSON object.")

    version = parsed.get("v")
    if version not in _PAGE_BODY_SUPPORTED_VERSIONS:
        raise serializers.ValidationError(
            f"Unsupported body version {version!r}; "
            f"supported: {sorted(_PAGE_BODY_SUPPORTED_VERSIONS)}."
        )

    sections = parsed.get("sections")
    if not isinstance(sections, list):
        raise serializers.ValidationError("body.sections must be an array.")

    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            raise serializers.ValidationError(
                f"body.sections[{idx}] must be an object."
            )
        for key in ("id", "kind", "value"):
            if key not in section:
                raise serializers.ValidationError(
                    f"body.sections[{idx}].{key} is required."
                )
            if not isinstance(section[key], str):
                raise serializers.ValidationError(
                    f"body.sections[{idx}].{key} must be a string."
                )
        if not section["id"].strip():
            raise serializers.ValidationError(
                f"body.sections[{idx}].id must be a non-empty string."
            )
        if not section["kind"].strip():
            raise serializers.ValidationError(
                f"body.sections[{idx}].kind must be a non-empty string."
            )

    return s


def _normalise_page_seo(raw) -> dict:
    """Keep documented SEO keys with the right types; drop everything else."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise serializers.ValidationError("seo must be a JSON object.")
    out: dict = {}
    if "description" in raw:
        value = raw["description"]
        if value is not None and not isinstance(value, str):
            raise serializers.ValidationError("seo.description must be a string.")
        if value:
            out["description"] = str(value).strip()[:500]
    if "ogImage" in raw:
        value = raw["ogImage"]
        if value is not None and not isinstance(value, str):
            raise serializers.ValidationError("seo.ogImage must be a string.")
        if value:
            out["ogImage"] = str(value).strip()[:500]
    if "noindex" in raw:
        value = raw["noindex"]
        if not isinstance(value, bool):
            raise serializers.ValidationError("seo.noindex must be a boolean.")
        out["noindex"] = value
    # Silently ignore any keys outside _PAGE_SEO_KEYS.
    _ = _PAGE_SEO_KEYS  # keep the list discoverable from code search
    return out


class PageReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = (
            "id",
            "slug",
            "title",
            "status",
            "body",
            "seo",
            "created_at",
            "updated_at",
        )


class PageCreateSerializer(serializers.Serializer):
    """Create payload for a new Page on a site (POST /sites/<slug>/pages/)."""

    slug = serializers.CharField(max_length=_PAGE_SLUG_MAX_LEN, allow_blank=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=Page.Status.choices,
        required=False,
        default=Page.Status.DRAFT,
    )
    body = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2_000_000,
    )
    seo = serializers.JSONField(required=False)

    def validate_slug(self, value: str) -> str:
        return _normalise_page_slug(value)

    def validate_title(self, value: str | None) -> str:
        return ("" if value is None else str(value)).strip()[:255]

    def validate_body(self, value: str | None) -> str:
        return _validate_page_body_json(value)

    def validate_seo(self, value) -> dict:
        return _normalise_page_seo(value)


class PagePatchSerializer(serializers.Serializer):
    """Update payload — every field optional; missing fields are left unchanged."""

    slug = serializers.CharField(max_length=_PAGE_SLUG_MAX_LEN, required=False, allow_blank=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Page.Status.choices, required=False)
    body = serializers.CharField(required=False, allow_blank=True, max_length=2_000_000)
    seo = serializers.JSONField(required=False)

    def validate_slug(self, value: str) -> str:
        return _normalise_page_slug(value)

    def validate_title(self, value: str | None) -> str:
        return ("" if value is None else str(value)).strip()[:255]

    def validate_body(self, value: str | None) -> str:
        return _validate_page_body_json(value)

    def validate_seo(self, value) -> dict:
        return _normalise_page_seo(value)

