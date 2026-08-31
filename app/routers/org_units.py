import csv
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.deps import AccountDep, DbDep, SuperAdminDep
from app.models import Account, Area, OrgUnit
from app.schemas import ImportResult, OrgUnitIn, OrgUnitOut, OrgUnitPatch
from app.security import hash_password

router = APIRouter(prefix="/org-units", tags=["org-units"])


@router.get("", response_model=list[OrgUnitOut])
async def list_units(
    _: AccountDep, db: DbDep, type: str | None = None, area: str | None = None
):
    q = select(OrgUnit).order_by(OrgUnit.name)
    if type in ("branch", "dept"):
        q = q.where(OrgUnit.unit_type == type)
    if area:
        q = q.where(OrgUnit.area_id == area)
    return list(await db.scalars(q))


@router.get("/{unit_id}", response_model=OrgUnitOut)
async def get_unit(unit_id: str, _: AccountDep, db: DbDep):
    unit = await db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return unit


@router.post("", response_model=OrgUnitOut, status_code=status.HTTP_201_CREATED)
async def create_unit(body: OrgUnitIn, _: SuperAdminDep, db: DbDep):
    if await db.get(Area, body.area_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown area")
    unit = OrgUnit(
        unit_type=body.unit_type, name=body.name, code=body.code, area_id=body.area_id
    )
    db.add(unit)
    try:
        await db.flush()
        db.add(
            Account(
                org_unit_id=unit.id,
                username=body.code,
                password_hash=hash_password(body.password),
            )
        )
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Duplicate code / username")
    return unit


@router.patch("/{unit_id}", response_model=OrgUnitOut)
async def update_unit(unit_id: str, body: OrgUnitPatch, _: SuperAdminDep, db: DbDep):
    unit = await db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if body.area_id is not None:
        if await db.get(Area, body.area_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown area")
        unit.area_id = body.area_id
    if body.name is not None:
        unit.name = body.name
    if body.code is not None and body.code != unit.code:
        # the unit's login username is seeded from its code at creation — keep it
        # in sync so the rename actually changes how the unit signs in
        await db.execute(
            update(Account)
            .where(Account.org_unit_id == unit.id, Account.username == unit.code)
            .values(username=body.code)
            .execution_options(synchronize_session=False)
        )
        unit.code = body.code
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Duplicate code / username")
    await db.refresh(unit)  # repopulate server-side updated_at before serialize
    return unit


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(unit_id: str, _: SuperAdminDep, db: DbDep):
    unit = await db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    await db.delete(unit)


def _col(row: dict[str, str], base: str, prefix: str) -> str:
    """Accept `name` or `branch_name` / `dept_name`."""
    return (row.get(base) or row.get(f"{prefix}_{base}") or "").strip()


@router.post("/import", response_model=ImportResult)
async def import_units(
    _: SuperAdminDep,
    db: DbDep,
    unit_type: str = Form(...),
    area_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Bulk create branches/depts under one area from an in-memory CSV.

    All-or-nothing: the whole file is validated first; on any error nothing is
    created. The uploaded bytes are never written to disk / storage / logs.
    """
    if unit_type not in ("branch", "dept"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unit_type must be branch|dept")
    if await db.get(Area, area_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown area")

    raw = await file.read()  # in-memory only; `file` (SpooledTemporaryFile) discarded on return
    try:
        text_io = io.StringIO(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "CSV must be UTF-8")
    reader = csv.DictReader(text_io)

    existing_codes = set(
        await db.scalars(select(OrgUnit.code).where(OrgUnit.unit_type == unit_type))
    )
    existing_usernames = set(await db.scalars(select(Account.username)))

    errors: list[dict] = []
    parsed: list[tuple[str, str, str]] = []
    seen_codes: set[str] = set()

    for i, row in enumerate(reader, start=2):  # row 1 = header
        name = _col(row, "name", unit_type)
        code = _col(row, "code", unit_type)
        password = _col(row, "password", unit_type)
        row_errs: list[str] = []
        if not name:
            row_errs.append("missing name")
        if not code:
            row_errs.append("missing code")
        if not password:
            row_errs.append("missing password")
        if code and code in seen_codes:
            row_errs.append("duplicate code within file")
        if code and code in existing_codes:
            row_errs.append("code already exists")
        if code and code in existing_usernames:
            row_errs.append("username (code) already taken")
        if row_errs:
            errors.append({"row": i, "errors": row_errs})
        else:
            seen_codes.add(code)
            parsed.append((name, code, password))

    if not parsed and not errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "CSV has no data rows")
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"errors": errors})

    for name, code, password in parsed:
        unit = OrgUnit(unit_type=unit_type, name=name, code=code, area_id=area_id)
        db.add(unit)
        await db.flush()
        db.add(
            Account(
                org_unit_id=unit.id,
                username=code,
                password_hash=hash_password(password),
            )
        )
    await db.flush()
    return ImportResult(created=len(parsed))
