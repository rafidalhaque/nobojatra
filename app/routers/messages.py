import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select

from app.deps import AccountDep, DbDep, require_permission
from app.models import Account, Message, OrgUnit
from app.schemas import ConversationOut, MessageIn, MessageOut

router = APIRouter(prefix="/messages", tags=["messages"])


def _require_unit(account: Account) -> None:
    if account.org_unit_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Messaging is per org unit")


@router.get("/conversations", response_model=list[ConversationOut])
async def conversations(account: AccountDep, db: DbDep):
    _require_unit(account)
    me = account.org_unit_id
    other = case((Message.sender_org_unit_id == me, Message.recipient_org_unit_id),
                 else_=Message.sender_org_unit_id).label("other")
    # RLS already restricts messages to those involving `me`.
    rows = (
        await db.execute(
            select(
                other,
                func.max(Message.created_at).label("last_at"),
                func.count().filter(
                    (Message.recipient_org_unit_id == me) & (Message.read_at.is_(None))
                ).label("unread"),
            ).group_by(other).order_by(func.max(Message.created_at).desc())
        )
    ).all()
    out = []
    for other_id, last_at, unread in rows:
        last_body = await db.scalar(
            select(Message.body)
            .where(
                or_(
                    (Message.sender_org_unit_id == me) & (Message.recipient_org_unit_id == other_id),
                    (Message.sender_org_unit_id == other_id) & (Message.recipient_org_unit_id == me),
                )
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        out.append(ConversationOut(org_unit_id=other_id, last_body=last_body or "", last_at=last_at, unread=unread))
    return out


@router.get("", response_model=list[MessageOut])
async def thread(account: AccountDep, db: DbDep, with_: str = Query(alias="with")):
    _require_unit(account)
    me = account.org_unit_id
    rows = await db.scalars(
        select(Message)
        .where(
            or_(
                (Message.sender_org_unit_id == me) & (Message.recipient_org_unit_id == with_),
                (Message.sender_org_unit_id == with_) & (Message.recipient_org_unit_id == me),
            )
        )
        .order_by(Message.created_at.asc())
    )
    return list(rows)


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    body: MessageIn,
    account: Account = Depends(require_permission("message.send")),
    db: DbDep = None,
):
    _require_unit(account)
    if body.recipient_org_unit_id == account.org_unit_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cannot message yourself")
    if await db.get(OrgUnit, body.recipient_org_unit_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown recipient")
    msg = Message(
        sender_org_unit_id=account.org_unit_id,
        recipient_org_unit_id=body.recipient_org_unit_id,
        sender_account_id=account.id,  # audit only, never serialized
        body=body.body,
    )
    db.add(msg)
    await db.flush()
    return msg


@router.post("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(message_id: str, account: AccountDep, db: DbDep):
    _require_unit(account)
    msg = await db.get(Message, message_id)
    if msg is None or msg.recipient_org_unit_id != account.org_unit_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if msg.read_at is None:
        msg.read_at = dt.datetime.now(dt.UTC)
    await db.flush()
