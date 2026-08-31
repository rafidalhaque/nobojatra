from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import AccountDep, DbDep, require_permission
from app.models import Category, Post
from app.schemas import CategoryIn, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])
_manage = Depends(require_permission("category.manage"))


@router.get("", response_model=list[CategoryOut])
async def list_categories(_: AccountDep, db: DbDep):
    return list(await db.scalars(select(Category).order_by(Category.name)))


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED, dependencies=[_manage])
async def create_category(body: CategoryIn, db: DbDep):
    cat = Category(name=body.name)
    db.add(cat)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Category name already exists")
    return cat


@router.patch("/{category_id}", response_model=CategoryOut, dependencies=[_manage])
async def rename_category(category_id: str, body: CategoryIn, db: DbDep):
    cat = await db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    cat.name = body.name
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Category name already exists")
    return cat


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_manage])
async def delete_category(category_id: str, db: DbDep):
    cat = await db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if await db.scalar(select(Post.id).where(Post.category_id == category_id).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Category still used by posts")
    await db.delete(cat)
