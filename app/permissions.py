"""Granular permission engine.

Actions are data, not hardcoded role checks. Effective value for a non-super account:
    org_unit override  ->  role default profile  ->  False
Super Admin bypasses this entirely (see spec 7 / 11.7).

profile.edit and area.manage are intentionally NOT in this catalog: they are
Super-Admin-only with no toggle (spec 7, 15).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, OrgUnit, OrgUnitPermission, PermissionProfile, ProfilePermission

# key -> human description (seeded into `permissions`)
CATALOG: dict[str, str] = {
    "post.create": "Create posts",
    "post.edit": "Edit own org unit's posts",
    "post.delete": "Delete own org unit's posts",
    "post.publish": "Publish / unpublish drafts",
    "message.send": "Send messages to any branch/dept",
    "category.manage": "Create, rename, delete categories",
    "profile.view": "View any branch/dept profile",
}

# spec 15 seed. dept_default = everything; branch_default = everything except category.manage.
PROFILE_DEFAULTS: dict[str, dict[str, bool]] = {
    "dept_default": {k: True for k in CATALOG},
    "branch_default": {k: (k != "category.manage") for k in CATALOG},
}


def _profile_name(unit_type: str) -> str:
    return "dept_default" if unit_type == "dept" else "branch_default"


async def has_permission(db: AsyncSession, account: Account, key: str) -> bool:
    if account.is_super_admin:
        return True
    if account.org_unit_id is None:
        return False

    override = await db.scalar(
        select(OrgUnitPermission.allowed).where(
            OrgUnitPermission.org_unit_id == account.org_unit_id,
            OrgUnitPermission.permission_key == key,
        )
    )
    if override is not None:
        return override

    unit = account.org_unit or await db.get(OrgUnit, account.org_unit_id)
    default = await db.scalar(
        select(ProfilePermission.allowed)
        .join(PermissionProfile, PermissionProfile.id == ProfilePermission.profile_id)
        .where(
            PermissionProfile.name == _profile_name(unit.unit_type),
            ProfilePermission.permission_key == key,
        )
    )
    return bool(default)
