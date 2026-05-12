from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from core.models import Account, AdminUser, Membership, Site, SiteContentSlot, SiteMedia, SiteMediaGroup, Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("api_key_hash", "created_at", "updated_at")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "workspace", "deleted_at", "created_at")
    list_filter = ("workspace",)
    search_fields = ("name", "slug", "workspace__slug")
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@admin.register(SiteContentSlot)
class SiteContentSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "site", "key", "label", "created_at")
    list_filter = ("key",)
    search_fields = ("label", "site__slug", "site__name")


@admin.register(SiteMediaGroup)
class SiteMediaGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "site", "name", "created_at")
    list_filter = ("site",)
    search_fields = ("name", "site__slug")


@admin.register(SiteMedia)
class SiteMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "site", "group", "kind", "original_name", "created_at")
    list_filter = ("site", "kind", "group")
    search_fields = ("original_name", "site__slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "account", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("workspace__slug", "workspace__name", "account__phone_number")


@admin.register(AdminUser)
class AdminUserAdmin(DjangoUserAdmin):
    ordering = ("username",)
    list_display = ("username", "is_staff", "is_superuser", "is_active")
    fieldsets = (
        (None, {"fields": ("username", "password", "new_password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "email",
        "account_type",
        "verification_status",
        "is_active",
    )
    search_fields = ("phone_number", "email", "first_name", "last_name")
    list_filter = ("account_type", "verification_status", "is_active")
