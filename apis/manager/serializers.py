from pathlib import Path

from django.utils.text import slugify
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from core.entities.sites.models import Site, SiteContentSlot, SiteMedia, SiteMediaGroup
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
        fields = ("id", "key", "type_label", "label", "body", "created_at", "updated_at")

    def get_type_label(self, obj: SiteContentSlot) -> str:
        try:
            return str(SiteContentSlot.SlotType(obj.key).label)
        except ValueError:
            return obj.key


class SiteContentSlotCreateSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=SiteContentSlot.SlotType.choices)
    label = serializers.CharField(max_length=255, required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True, max_length=500_000)

    def validate_label(self, value: str) -> str:
        return (value or "").strip()

    def validate_body(self, value: str) -> str:
        return value or ""


class SiteContentSlotPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteContentSlot
        fields = ("label", "body")

    def validate_label(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def validate_body(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value)


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
