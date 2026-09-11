import datetime as dt
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, or_, select

from app import storage
from app.deps import AccountDep, DbDep, require_permission
from app.models import Account, Message, MessageAttachment, OrgUnit
from app.schemas import ConversationOut, MessageOut

router = APIRouter(prefix="/messages", tags=["messages"])

# Types safe to render in the browser; everything else forced to download as an
# opaque blob (mirrors app/routers/posts.py get_media — same reasoning).
_INLINE_OK = ("image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf")


async def _acting_unit(account: Account, db, as_unit: str | None) -> uuid.UUID:
    """The org unit this request speaks for. A branch/dept account is always its
    own unit and cannot spoof another. A Super Admin has no unit, so they pass
    one to act as via `?as=` / `sender_org_unit_id` — restricted to a department."""
    if account.org_unit_id is not None:
        return account.org_unit_id
    if not account.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Messaging is per org unit")
    if not as_unit:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a department to message as")
    unit = await db.get(OrgUnit, as_unit)
    if unit is None or unit.unit_type != "dept":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message-as unit must be a department")
    return unit.id


@router.get("/conversations", response_model=list[ConversationOut])
async def conversations(account: AccountDep, db: DbDep, as_: str | None = Query(default=None, alias="as")):
    me = await _acting_unit(account, db, as_)
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
async def thread(
    account: AccountDep,
    db: DbDep,
    with_: str = Query(alias="with"),
    as_: str | None = Query(default=None, alias="as"),
):
    me = await _acting_unit(account, db, as_)
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
    recipient_org_unit_id: uuid.UUID = Form(...),
    body: str = Form(default=""),
    # Super Admin only: the department to send as. Ignored for branch/dept
    # accounts (they always send as their own unit).
    sender_org_unit_id: uuid.UUID | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    account: Account = Depends(require_permission("message.send")),
    db: DbDep = None,
):
    body = body.strip()
    files = [f for f in files if f.filename]
    if not body and not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message needs text or an attachment")
    me = await _acting_unit(account, db, sender_org_unit_id)
    if recipient_org_unit_id == me:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cannot message yourself")
    if await db.get(OrgUnit, recipient_org_unit_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown recipient")
    msg = Message(
        sender_org_unit_id=me,
        recipient_org_unit_id=recipient_org_unit_id,
        sender_account_id=account.id,  # audit only, never serialized
        body=body,
    )
    msg.attachments = [
        MessageAttachment(
            s3_key=storage.put(f.file, f.content_type, prefix="messages"),
            original_filename=f.filename or "file",
            content_type=f.content_type,
            size_bytes=f.size or 0,
        )
        for f in files
    ]
    db.add(msg)
    await db.flush()
    return msg


@router.post("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    message_id: str,
    account: AccountDep,
    db: DbDep,
    as_: str | None = Query(default=None, alias="as"),
):
    me = await _acting_unit(account, db, as_)
    msg = await db.get(Message, message_id)
    if msg is None or msg.recipient_org_unit_id != me:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if msg.read_at is None:
        msg.read_at = dt.datetime.now(dt.UTC)
    await db.flush()


@router.get("/attachments/{attachment_id}")
async def get_attachment(attachment_id: str, account: AccountDep, db: DbDep):
    """Auth-gated proxy, no public S3 URLs (spec 11.2). Visibility rides on the
    parent message's RLS, same as posts' get_media."""
    att = await db.get(MessageAttachment, attachment_id)
    if att is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if await db.get(Message, att.message_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    chunks, content_type, length = storage.open_stream(att.s3_key)

    ct = (content_type or "").split(";")[0].strip().lower()
    inline = ct in _INLINE_OK
    served_type = ct if inline else "application/octet-stream"
    filename = quote(att.original_filename or "file", safe="")

    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox; base-uri 'none'",
        "Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{filename}",
    }
    if length is not None:
        headers["Content-Length"] = str(length)
    return StreamingResponse(chunks, media_type=served_type, headers=headers)
