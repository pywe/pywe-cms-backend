from core.entities.workspaces.models import Membership, Workspace


def get_owner_workspace(account) -> Workspace | None:
    """Resolve the workspace this account owns, if any (manager plane)."""
    row = (
        Membership.objects.filter(
            account=account,
            role=Membership.Role.OWNER,
        )
        .select_related("workspace")
        .first()
    )
    return row.workspace if row else None


def get_manager_membership(account) -> Membership | None:
    """Any workspace membership for manager-scoped APIs (owner or editor)."""
    return (
        Membership.objects.filter(account=account)
        .select_related("workspace")
        .order_by("id")
        .first()
    )


def manager_may_mutate_sites(membership: Membership) -> bool:
    """Whether the member may create, update, or soft-delete sites.

    Today: owners only. Extend here (e.g. grant editors) when product rules are defined.
    """
    return membership.role == Membership.Role.OWNER
