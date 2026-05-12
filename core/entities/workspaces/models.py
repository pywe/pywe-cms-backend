import hashlib
import secrets

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.entities.common.models import TimeStamp
from core.entities.users.models import Account


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_workspace_api_key() -> tuple[str, str]:
    raw = f"pcm_{secrets.token_urlsafe(32)}"
    return raw, hash_api_key(raw)


class Workspace(TimeStamp):
    """Tenant root (Kosoton `Store` analogue). Content models will FK here."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=96, unique=True)
    is_active = models.BooleanField(default=True)
    api_key_hash = models.CharField(max_length=64, unique=True, editable=False)

    class Meta:
        app_label = "core"
        db_table = "workspace"

    def rotate_api_key(self) -> str:
        """Persist a new key hash; return plaintext once (caller must expose to user)."""
        raw, hashed = generate_workspace_api_key()
        self.api_key_hash = hashed
        self.save(update_fields=["api_key_hash", "updated_at"])
        return raw


class Membership(TimeStamp):
    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        EDITOR = "editor", _("Editor")

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EDITOR)

    class Meta:
        app_label = "core"
        db_table = "workspace_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "account"],
                name="uniq_workspace_membership_account",
            ),
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(role="owner"),
                name="uniq_owner_membership_per_account",
            ),
            models.UniqueConstraint(
                fields=["workspace"],
                condition=models.Q(role="owner"),
                name="uniq_one_owner_per_workspace",
            ),
        ]
