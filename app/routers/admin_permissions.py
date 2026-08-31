"""Permission-matrix admin (spec 6, 8.1). Super Admin edits the two role
defaults and per-unit overrides live — no deploy, no CLI, no DB edit."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import DbDep, SuperAdminDep
from app.models import OrgUnit, OrgUnitPermission, PermissionProfile, ProfilePermission
from app.permissions import CATALOG, has_permission
from app.schemas import EffectiveMatrixOut, MatrixIn, PermissionOut, UnitMatrixIn

router = APIRouter(tags=["permissions"])
_PROFILES = ("dept_default", "branch_default")


@router.get("/permissions", response_model=list[PermissionOut])
async def catalog(_: SuperAdminDep):
    return [PermissionOut(key=k, description=v) for k, v in CATALOG.items()]


@router.get("/permission-profiles/{name}", response_model=dict[str, bool])
async def get_profile(name: str, _: SuperAdminDep, db: DbDep):
    if name not in _PROFILES:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    prof = await db.scalar(select(PermissionProfile).where(PermissionProfile.name == name))
    rows = await db.execute(
        select(ProfilePermission.permission_key, ProfilePermission.allowed).where(
            ProfilePermission.profile_id == prof.id
        )
    )
    current = dict(rows.all())
    return {k: current.get(k, False) for k in CATALOG}


@router.put("/permission-profiles/{name}/permissions", response_model=dict[str, bool])
async def set_profile(name: str, body: MatrixIn, _: SuperAdminDep, db: DbDep):
    if name not in _PROFILES:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    unknown = set(body.permissions) - set(CATALOG)
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown keys: {sorted(unknown)}")
    prof = await db.scalar(select(PermissionProfile).where(PermissionProfile.name == name))
    existing = {
        r.permission_key: r
        for r in await db.scalars(
            select(ProfilePermission).where(ProfilePermission.profile_id == prof.id)
        )
    }
    for key, allowed in body.permissions.items():
        if key in existing:
            existing[key].allowed = allowed
        else:
            db.add(ProfilePermission(profile_id=prof.id, permission_key=key, allowed=allowed))
    await db.flush()
    return await get_profile(name, _, db)


@router.get("/org-units/{unit_id}/permissions", response_model=EffectiveMatrixOut)
async def get_unit_permissions(unit_id: str, account: SuperAdminDep, db: DbDep):
    unit = await db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    overrides = dict(
        (
            await db.execute(
                select(OrgUnitPermission.permission_key, OrgUnitPermission.allowed).where(
                    OrgUnitPermission.org_unit_id == unit_id
                )
            )
        ).all()
    )
    # reuse the real engine so "effective" always matches runtime checks
    fake = type("A", (), {"is_super_admin": False, "org_unit_id": unit.id, "org_unit": unit})()
    effective = {k: await has_permission(db, fake, k) for k in CATALOG}
    return EffectiveMatrixOut(unit_type=unit.unit_type, effective=effective, overrides=overrides)


@router.put("/org-units/{unit_id}/permissions", response_model=EffectiveMatrixOut)
async def set_unit_permissions(unit_id: str, body: UnitMatrixIn, account: SuperAdminDep, db: DbDep):
    unit = await db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    unknown = set(body.permissions) - set(CATALOG)
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown keys: {sorted(unknown)}")
    existing = {
        r.permission_key: r
        for r in await db.scalars(
            select(OrgUnitPermission).where(OrgUnitPermission.org_unit_id == unit_id)
        )
    }
    for key, allowed in body.permissions.items():
        if allowed is None:  # clear override -> inherit profile default
            if key in existing:
                await db.delete(existing[key])
        elif key in existing:
            existing[key].allowed = allowed
        else:
            db.add(OrgUnitPermission(org_unit_id=unit_id, permission_key=key, allowed=allowed))
    await db.flush()
    return await get_unit_permissions(unit_id, account, db)
