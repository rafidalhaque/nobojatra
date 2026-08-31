from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import AccountDep, DbDep, SuperAdminDep
from app.models import Area, OrgUnit
from app.schemas import AreaIn, AreaOut

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=list[AreaOut])
async def list_areas(_: AccountDep, db: DbDep):
    return list(await db.scalars(select(Area).order_by(Area.name)))


@router.post("", response_model=AreaOut, status_code=status.HTTP_201_CREATED)
async def create_area(body: AreaIn, _: SuperAdminDep, db: DbDep):
    area = Area(name=body.name)
    db.add(area)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Area name already exists")
    return area


@router.patch("/{area_id}", response_model=AreaOut)
async def rename_area(area_id: str, body: AreaIn, _: SuperAdminDep, db: DbDep):
    area = await db.get(Area, area_id)
    if area is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    area.name = body.name
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Area name already exists")
    return area


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_area(area_id: str, _: SuperAdminDep, db: DbDep):
    area = await db.get(Area, area_id)
    if area is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    in_use = await db.scalar(select(OrgUnit.id).where(OrgUnit.area_id == area_id).limit(1))
    if in_use:
        raise HTTPException(status.HTTP_409_CONFLICT, "Area still has branches/depts")
    await db.delete(area)
