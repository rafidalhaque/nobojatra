import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.deps import AccountDep, DbDep
from app.models import Notification
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(account: AccountDep, db: DbDep, status_: str | None = None):
    # RLS restricts rows to this org unit already.
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if status_ in ("read", "unread"):
        stmt = stmt.where(Notification.status == status_)
    return list(await db.scalars(stmt))


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(notification_id: str, account: AccountDep, db: DbDep):
    n = await db.get(Notification, notification_id)
    if n is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if n.status == "unread":
        n.status = "read"
        n.read_at = dt.datetime.now(dt.UTC)
    await db.flush()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(account: AccountDep, db: DbDep):
    await db.execute(
        update(Notification)
        .where(Notification.status == "unread")
        .values(status="read", read_at=dt.datetime.now(dt.UTC))
    )
