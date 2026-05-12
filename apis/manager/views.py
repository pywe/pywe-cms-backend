import logging
import random

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apis.manager.resolver import (
    get_manager_membership,
    get_owner_workspace,
    manager_may_mutate_sites,
)
from apis.manager.serializers import (
    ManagerOtpRequestSerializer,
    ManagerOtpVerifySerializer,
    ManagerProfilePatchSerializer,
    ManagerRegisterSerializer,
    SiteContentSlotCreateSerializer,
    SiteContentSlotPatchSerializer,
    SiteContentSlotReadSerializer,
    SiteMediaBulkDeleteSerializer,
    SiteMediaBulkGroupSerializer,
    SiteMediaCreateSerializer,
    SiteMediaGroupCreateSerializer,
    SiteMediaGroupPatchSerializer,
    SiteMediaGroupSerializer,
    SiteMediaReadSerializer,
    SiteCreateSerializer,
    SitePatchSerializer,
    SiteReadSerializer,
    WorkspaceCreateSerializer,
    WorkspaceReadSerializer,
)
from apis.utils import envelope
from core.entities.sites.models import CONTENT_SLOT_TYPE_HINTS, Site, SiteContentSlot, SiteMedia, SiteMediaGroup
from core.entities.users.models import Account
from core.entities.workspaces.models import Membership, Workspace, generate_workspace_api_key
from utils.sms import SMSNotification, SMSTemplate

logger = logging.getLogger(__name__)
OTP_CACHE_KEY_PREFIX = "manager:otp:"
OTP_TTL_SECONDS = 300


def _otp_cache_key(phone_number: str) -> str:
    return f"{OTP_CACHE_KEY_PREFIX}{phone_number}"


def _generate_otp_code() -> str:
    return f"{random.randint(0, 999999):06d}"


class ManagerRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ManagerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account: Account = serializer.save()
        refresh = RefreshToken.for_user(account)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": account.pk,
            },
            status=status.HTTP_201_CREATED,
        )


def _account_profile_payload(account: Account) -> dict:
    return {
        "profile_complete": account.is_manager_signup_profile_complete(),
        "first_name": account.first_name or "",
        "last_name": account.last_name or "",
        "email": str(account.email) if account.email else "",
    }


class ManagerProfileView(APIView):
    """Read/update Account profile for manager onboarding (name + email)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            envelope(True, data=_account_profile_payload(account)),
            status=status.HTTP_200_OK,
        )

    def patch(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ManagerProfilePatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account.first_name = serializer.validated_data["first_name"]
        account.last_name = serializer.validated_data["last_name"]
        account.email = serializer.validated_data["email"]
        account.save(update_fields=["first_name", "last_name", "email", "updated_at"])
        return Response(
            envelope(
                True,
                data=_account_profile_payload(account),
                message="Profile saved.",
            ),
            status=status.HTTP_200_OK,
        )


class WorkspaceListCreateView(APIView):
    """Create a workspace (tenant) for the authenticated Account; one owner per account."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None:
            return Response(
                envelope(
                    True,
                    data={"workspace": None, "membership_role": None},
                ),
                status=status.HTTP_200_OK,
            )
        return Response(
            envelope(
                True,
                data={
                    "workspace": WorkspaceReadSerializer(membership.workspace).data,
                    "membership_role": membership.role,
                },
            ),
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if get_owner_workspace(account) is not None:
            return Response(
                {"detail": "This account already owns a workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_key, key_hash = generate_workspace_api_key()
        workspace = Workspace.objects.create(
            name=serializer.validated_data["name"],
            slug=serializer.validated_data["slug"],
            api_key_hash=key_hash,
        )
        Membership.objects.create(
            workspace=workspace,
            account=account,
            role=Membership.Role.OWNER,
        )
        return Response(
            envelope(
                True,
                data={
                    "workspace": WorkspaceReadSerializer(workspace).data,
                    "membership_role": Membership.Role.OWNER,
                    "api_key": raw_key,
                },
                message="Store the api_key securely; it cannot be shown again.",
            ),
            status=status.HTTP_201_CREATED,
        )


class SiteListCreateView(APIView):
    """List sites for the caller's workspace, or create one (owner only)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None:
            return Response(
                envelope(True, data={"sites": []}),
                status=status.HTTP_200_OK,
            )
        sites = Site.objects.filter(workspace=membership.workspace).order_by("name")
        return Response(
            envelope(True, data={"sites": SiteReadSerializer(sites, many=True).data}),
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None:
            return Response(
                {"detail": "No workspace membership for this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can create sites."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SiteCreateSerializer(data=request.data, context={"workspace": membership.workspace})
        serializer.is_valid(raise_exception=True)
        site = Site.objects.create(
            workspace=membership.workspace,
            name=serializer.validated_data["name"],
            slug=serializer.validated_data["slug"],
            description=serializer.validated_data.get("description") or "",
            primary_url=serializer.validated_data.get("primary_url") or "",
        )
        return Response(
            envelope(
                True,
                data={"site": SiteReadSerializer(site).data},
                message="Site created.",
            ),
            status=status.HTTP_201_CREATED,
        )


class SiteDetailView(APIView):
    """Retrieve, update, or soft-delete a site (mutations: owner only)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, site_slug, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None:
            return Response(
                {"detail": "No workspace membership for this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        site = Site.objects.filter(workspace=membership.workspace, slug=site_slug).first()
        if site is None:
            return Response(
                {"detail": "Site not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            envelope(True, data={"site": SiteReadSerializer(site).data}),
            status=status.HTTP_200_OK,
        )

    def patch(self, request, site_slug, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None:
            return Response(
                {"detail": "No workspace membership for this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can update sites."},
                status=status.HTTP_403_FORBIDDEN,
            )
        site = Site.objects.filter(workspace=membership.workspace, slug=site_slug).first()
        if site is None:
            return Response(
                {"detail": "Site not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SitePatchSerializer(
            site,
            data=request.data,
            partial=True,
            context={"workspace": membership.workspace},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            envelope(True, data={"site": SiteReadSerializer(site).data}, message="Site updated."),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, site_slug, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None:
            return Response(
                {"detail": "No workspace membership for this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can delete sites."},
                status=status.HTTP_403_FORBIDDEN,
            )
        site = Site.all_objects.filter(workspace=membership.workspace, slug=site_slug).first()
        if site is None or site.deleted_at is not None:
            return Response(
                {"detail": "Site not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        site.deleted_at = timezone.now()
        site.save(update_fields=["deleted_at", "updated_at"])
        return Response(
            envelope(True, message="Site removed."),
            status=status.HTTP_200_OK,
        )


def _manager_site_for_slug(account, site_slug: str):
    """Return (membership, site) or (None, error Response)."""
    if not isinstance(account, Account):
        return None, Response(
            {"detail": "Manager endpoints require an Account bearer token."},
            status=status.HTTP_403_FORBIDDEN,
        )
    membership = get_manager_membership(account)
    if membership is None:
        return None, Response(
            {"detail": "No workspace membership for this account."},
            status=status.HTTP_403_FORBIDDEN,
        )
    site = Site.objects.filter(workspace=membership.workspace, slug=site_slug).first()
    if site is None:
        return None, Response(
            {"detail": "Site not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return (membership, site), None


class SiteMediaListCreateView(APIView):
    """List site media (images and videos) or upload a new file for the library."""

    permission_classes = [IsAuthenticated]

    def get(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        _membership, site = pair
        rows = SiteMedia.objects.filter(site=site).select_related("group").order_by("-created_at", "-id")
        kind = (request.query_params.get("kind") or "").strip().lower()
        if kind in (SiteMedia.MediaKind.IMAGE, SiteMedia.MediaKind.VIDEO):
            rows = rows.filter(kind=kind)
        group = (request.query_params.get("group") or "").strip().lower()
        if group in ("none", "ungrouped"):
            rows = rows.filter(group__isnull=True)
        elif group.isdigit():
            rows = rows.filter(group_id=int(group))
        return Response(
            envelope(
                True,
                data={"media": SiteMediaReadSerializer(rows, many=True, context={"request": request}).data},
            ),
            status=status.HTTP_200_OK,
        )

    def post(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can upload media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SiteMediaCreateSerializer(data=request.data, context={"site": site, "request": request})
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        kind = serializer.validated_data["kind"]
        original = (getattr(uploaded, "name", None) or "")[:255]
        gid = serializer.validated_data.get("group_id")
        group_obj = None
        if gid is not None:
            group_obj = SiteMediaGroup.objects.filter(pk=gid, site=site).first()
        media = SiteMedia.objects.create(
            site=site,
            file=uploaded,
            original_name=original,
            kind=kind,
            group=group_obj,
        )
        label = "Video" if kind == SiteMedia.MediaKind.VIDEO else "Image"
        return Response(
            envelope(
                True,
                data={
                    "media": SiteMediaReadSerializer(
                        SiteMedia.objects.select_related("group").get(pk=media.pk),
                        context={"request": request},
                    ).data
                },
                message=f"{label} uploaded.",
            ),
            status=status.HTTP_201_CREATED,
        )


class SiteMediaGroupListCreateView(APIView):
    """List or create media groups for a site."""

    permission_classes = [IsAuthenticated]

    def get(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        _membership, site = pair
        qs = (
            SiteMediaGroup.objects.filter(site=site)
            .annotate(media_count=Count("media_items", distinct=True))
            .order_by("name", "id")
        )
        return Response(
            envelope(True, data={"groups": SiteMediaGroupSerializer(qs, many=True).data}),
            status=status.HTTP_200_OK,
        )

    def post(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can manage media groups."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SiteMediaGroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        if SiteMediaGroup.objects.filter(site=site, name=name).exists():
            return Response(
                {"detail": "A group with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        group = SiteMediaGroup.objects.create(site=site, name=name)
        group.media_count = 0
        return Response(
            envelope(
                True,
                data={"group": SiteMediaGroupSerializer(group).data},
                message="Group created.",
            ),
            status=status.HTTP_201_CREATED,
        )


class SiteMediaGroupDetailView(APIView):
    """Rename or delete a media group."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, site_slug, group_id, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can manage media groups."},
                status=status.HTTP_403_FORBIDDEN,
            )
        group = SiteMediaGroup.objects.filter(pk=group_id, site=site).first()
        if group is None:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SiteMediaGroupPatchSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_name = serializer.validated_data.get("name")
        if new_name is not None:
            if (
                SiteMediaGroup.objects.filter(site=site, name=new_name)
                .exclude(pk=group.pk)
                .exists()
            ):
                return Response(
                    {"detail": "A group with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer.save()
        refreshed = (
            SiteMediaGroup.objects.filter(pk=group.pk)
            .annotate(media_count=Count("media_items", distinct=True))
            .first()
        )
        return Response(
            envelope(
                True,
                data={"group": SiteMediaGroupSerializer(refreshed).data},
                message="Group updated.",
            ),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, site_slug, group_id, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can manage media groups."},
                status=status.HTTP_403_FORBIDDEN,
            )
        group = SiteMediaGroup.objects.filter(pk=group_id, site=site).first()
        if group is None:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
        SiteMedia.objects.filter(group=group).update(group=None)
        group.delete()
        return Response(
            envelope(True, message="Group removed. Files are now ungrouped."),
            status=status.HTTP_200_OK,
        )


class SiteMediaBulkGroupView(APIView):
    """Assign many media rows to a group (or clear their group)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can move media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SiteMediaBulkGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["media_ids"]
        gid = serializer.validated_data.get("group_id")
        group_obj = None
        if gid is not None:
            group_obj = SiteMediaGroup.objects.filter(pk=gid, site=site).first()
            if group_obj is None:
                return Response({"detail": "Unknown group for this site."}, status=status.HTTP_400_BAD_REQUEST)
        qs = SiteMedia.objects.filter(site=site, pk__in=ids)
        found = qs.count()
        if found != len(set(ids)):
            return Response(
                {"detail": "One or more media IDs are missing or do not belong to this site."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = qs.update(group=group_obj)
        return Response(
            envelope(True, data={"updated": updated}, message=f"Updated {updated} file(s)."),
            status=status.HTTP_200_OK,
        )


class SiteMediaBulkDeleteView(APIView):
    """Permanently delete site media files (storage + rows)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can delete media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SiteMediaBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["media_ids"]
        qs = SiteMedia.objects.filter(site=site, pk__in=ids)
        if qs.count() != len(set(ids)):
            return Response(
                {"detail": "One or more media IDs are missing or do not belong to this site."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rows = list(qs)
        for media in rows:
            if media.file:
                media.file.delete(save=False)
        deleted, _ = SiteMedia.objects.filter(site=site, pk__in=[m.pk for m in rows]).delete()
        return Response(
            envelope(True, data={"deleted": deleted}, message=f"Deleted {deleted} file(s)."),
            status=status.HTTP_200_OK,
        )


class SiteContentSlotTypesView(APIView):
    """Predefined slot types for the manager UI (key, label, content hint)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        slot_types = [
            {
                "key": choice.value,
                "label": str(choice.label),
                "hint": CONTENT_SLOT_TYPE_HINTS.get(choice.value, ""),
            }
            for choice in SiteContentSlot.SlotType
        ]
        return Response(
            envelope(True, data={"slot_types": slot_types}),
            status=status.HTTP_200_OK,
        )


class SiteContentSlotListCreateView(APIView):
    """List or create content slots for a site (keyed copy for headless consumers)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        _membership, site = pair
        slots = SiteContentSlot.objects.filter(site=site)
        key_filter = (request.query_params.get("key") or "").strip()
        if key_filter:
            allowed_keys = {c.value for c in SiteContentSlot.SlotType}
            if key_filter not in allowed_keys:
                return Response(
                    {"detail": "Invalid key filter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            slots = slots.filter(key=key_filter)
        slots = slots.order_by("key", "id")
        return Response(
            envelope(True, data={"slots": SiteContentSlotReadSerializer(slots, many=True).data}),
            status=status.HTTP_200_OK,
        )

    def post(self, request, site_slug, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can create content slots."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SiteContentSlotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data["key"]
        raw_label = (serializer.validated_data.get("label") or "").strip()
        default_label = str(SiteContentSlot.SlotType(key).label)
        label = raw_label if raw_label else default_label
        slot = SiteContentSlot.objects.create(
            site=site,
            key=key,
            label=label,
            body=serializer.validated_data.get("body") or "",
        )
        return Response(
            envelope(
                True,
                data={"slot": SiteContentSlotReadSerializer(slot).data},
                message="Content slot created.",
            ),
            status=status.HTTP_201_CREATED,
        )


class SiteContentSlotDetailView(APIView):
    """Read, update, or delete a single content slot."""

    permission_classes = [IsAuthenticated]

    def get(self, request, site_slug, slot_id, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        _membership, site = pair
        slot = SiteContentSlot.objects.filter(site=site, pk=slot_id).first()
        if slot is None:
            return Response({"detail": "Slot not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            envelope(True, data={"slot": SiteContentSlotReadSerializer(slot).data}),
            status=status.HTTP_200_OK,
        )

    def patch(self, request, site_slug, slot_id, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can update content slots."},
                status=status.HTTP_403_FORBIDDEN,
            )
        slot = SiteContentSlot.objects.filter(site=site, pk=slot_id).first()
        if slot is None:
            return Response({"detail": "Slot not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SiteContentSlotPatchSerializer(slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            envelope(True, data={"slot": SiteContentSlotReadSerializer(slot).data}, message="Slot updated."),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, site_slug, slot_id, *args, **kwargs):
        account = request.user
        pair, err = _manager_site_for_slug(account, site_slug)
        if err:
            return err
        membership, site = pair
        if not manager_may_mutate_sites(membership):
            return Response(
                {"detail": "Only a workspace owner can delete content slots."},
                status=status.HTTP_403_FORBIDDEN,
            )
        deleted, _ = SiteContentSlot.objects.filter(site=site, pk=slot_id).delete()
        if not deleted:
            return Response({"detail": "Slot not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(envelope(True, message="Slot removed."), status=status.HTTP_200_OK)


class WorkspaceRotateApiKeyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        account = request.user
        if not isinstance(account, Account):
            return Response(
                {"detail": "Manager endpoints require an Account bearer token."},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_manager_membership(account)
        if membership is None or membership.role != Membership.Role.OWNER:
            return Response(
                {"detail": "Only the workspace owner can rotate the API key."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ws = membership.workspace
        raw = ws.rotate_api_key()
        return Response(
            envelope(
                True,
                data={"api_key": raw},
                message="Previous key is invalidated. Store the new api_key securely.",
            ),
            status=status.HTTP_200_OK,
        )


class ManagerOtpRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ManagerOtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = str(serializer.validated_data["phone_number"])

        code = _generate_otp_code()
        cache_key = _otp_cache_key(phone_number)
        sms_message = SMSTemplate().customer_login_otp(code)
        if settings.SMS_GATEWAY_CONFIGURED:
            try:
                SMSNotification().send_sms({"body": sms_message, "phones": phone_number})
            except Exception:
                logger.exception("Manager OTP SMS send failed for %s", phone_number)
                return Response(
                    {"detail": "Could not send verification SMS. Try again shortly."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        cache.set(cache_key, code, timeout=OTP_TTL_SECONDS)
        if not settings.SMS_GATEWAY_CONFIGURED:
            logger.warning("SMS_GATEWAY_CONFIGURED=false; OTP for %s: %s", phone_number, code)

        return Response(
            {
                "success": True,
                "message": "Verification code sent.",
            },
            status=status.HTTP_200_OK,
        )


class ManagerOtpVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ManagerOtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = str(serializer.validated_data["phone_number"])
        provided_code = serializer.validated_data["code"]

        cached_code = cache.get(_otp_cache_key(phone_number))
        if not cached_code:
            return Response(
                {"detail": "Code expired or not requested."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if cached_code != provided_code:
            return Response(
                {"detail": "Invalid verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache.delete(_otp_cache_key(phone_number))
        account, _created = Account.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                "verification_status": Account.VerificationStatus.VERIFIED,
                "account_type": Account.AccountType.MERCHANT,
                "is_active": True,
            },
        )
        if account.verification_status != Account.VerificationStatus.VERIFIED:
            account.verification_status = Account.VerificationStatus.VERIFIED
            account.save(update_fields=["verification_status", "updated_at"])

        refresh = RefreshToken.for_user(account)
        payload = _account_profile_payload(account)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": account.pk,
                **payload,
            },
            status=status.HTTP_200_OK,
        )
